"""Compact, column-oriented storage for race replay frames.

A race has ~150k frames (25 FPS) x 20 drivers. Storing every frame as nested
dicts costs gigabytes of RAM and makes the cache file slow to load. FrameStore
keeps the same data in numpy arrays and only builds the familiar frame dict
(``{"t", "lap", "drivers": {code: {...}}, "weather", "safety_car"}``) for the
frame that is actually requested, so existing code that does
``frames[i]["drivers"][code]["x"]`` keeps working unchanged.
"""

import numpy as np

# Per-driver fields in the order they appear in each driver dict, with the
# dtype used for storage.
DRIVER_FIELDS = (
    ("x", np.float32),
    ("y", np.float32),
    ("dist", np.float64),
    ("lap", np.int16),
    ("rel_dist", np.float32),
    ("tyre", np.float32),
    ("tyre_life", np.float32),
    ("position", np.int16),
    ("speed", np.float32),
    ("gear", np.int16),
    ("drs", np.int16),
    ("throttle", np.float32),
    ("brake", np.float32),
    ("in_pit", np.bool_),
)

WEATHER_FIELDS = ("track_temp", "air_temp", "humidity", "wind_speed", "wind_direction")

SC_PHASES = ("deploying", "on_track", "returning")


class FrameStore:
    """Sequence of replay frames backed by numpy arrays.

    Behaves like a read-only list of frame dicts: supports ``len``, integer
    and slice indexing and iteration. Use the arrays directly (``t``,
    ``leader_lap``, ``columns``) for whole-race scans.
    """

    def __init__(self, t, leader_lap, codes, order, columns, weather=None):
        self.t = t                      # (n,) float64, seconds since start
        self.leader_lap = leader_lap    # (n,) int16
        self.codes = list(codes)        # driver codes, column order
        self.order = order              # (n, d) int8: driver columns by position
        self.columns = columns          # field -> (n, d) array
        self.weather = weather          # field -> (n,) array, or None
        self.sc_active = None           # (n,) bool, set by set_safety_car_arrays
        self.sc_x = self.sc_y = self.sc_alpha = self.sc_phase = None
        self._cache_idx = -1
        self._cache_frame = None

    # -- sequence protocol -------------------------------------------------

    def __len__(self):
        return len(self.t)

    def __bool__(self):
        return len(self.t) > 0

    def __iter__(self):
        for i in range(len(self.t)):
            yield self._build(i)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return [self._build(i) for i in range(*key.indices(len(self.t)))]
        i = int(key)
        if i < 0:
            i += len(self.t)
        if not 0 <= i < len(self.t):
            raise IndexError("frame index out of range")
        # The replay asks for the same frame several times per draw.
        if i != self._cache_idx:
            self._cache_frame = self._build(i)
            self._cache_idx = i
        return self._cache_frame

    def _build(self, i):
        order = self.order[i].tolist()
        codes = self.codes
        rows = [(name, self.columns[name][i].tolist()) for name, _ in DRIVER_FIELDS]
        drivers = {}
        for j in order:
            drivers[codes[j]] = {name: values[j] for name, values in rows}

        frame = {
            "t": float(self.t[i]),
            "lap": int(self.leader_lap[i]),
            "drivers": drivers,
        }
        if self.weather is not None:
            w = self.weather
            snapshot = {name: (float(w[name][i]) if name in w else None) for name in WEATHER_FIELDS}
            rain = float(w["rainfall"][i]) if "rainfall" in w else 0.0
            snapshot["rain_state"] = "RAINING" if rain and rain >= 0.5 else "DRY"
            frame["weather"] = snapshot
        if self.sc_active is not None:
            if self.sc_active[i]:
                frame["safety_car"] = {
                    "x": float(self.sc_x[i]),
                    "y": float(self.sc_y[i]),
                    "phase": SC_PHASES[int(self.sc_phase[i])],
                    "alpha": float(self.sc_alpha[i]),
                }
            else:
                frame["safety_car"] = None
        return frame

    # -- helpers -----------------------------------------------------------

    @property
    def has_weather(self):
        return self.weather is not None

    def set_safety_car_arrays(self, active, x, y, phase, alpha):
        self.sc_active = np.asarray(active, dtype=np.bool_)
        self.sc_x = np.round(np.asarray(x, dtype=np.float64), 2)
        self.sc_y = np.round(np.asarray(y, dtype=np.float64), 2)
        self.sc_phase = np.asarray(phase, dtype=np.int8)
        self.sc_alpha = np.round(np.asarray(alpha, dtype=np.float32), 3)
        self._cache_idx = -1

    def __getstate__(self):
        state = self.__dict__.copy()
        state["_cache_idx"] = -1
        state["_cache_frame"] = None
        return state


def frames_have_weather(frames):
    if isinstance(frames, FrameStore):
        return frames.has_weather
    return any("weather" in frame for frame in frames) if frames else False


def build_frame_store(timeline, resampled_data, pit_windows, weather_resampled=None):
    """Vectorised equivalent of building one dict per frame.

    Positions are ordered by (lap, race distance), leader first, exactly like
    the per-frame sort it replaces.
    """
    codes = list(resampled_data.keys())
    n = len(timeline)

    def stack(name):
        return np.column_stack([resampled_data[c][name] for c in codes]) if codes else np.empty((n, 0))

    lap = np.rint(stack("lap")).astype(np.int16)
    dist = stack("dist").astype(np.float64)

    # Descending by lap, then by distance; ties keep driver order (stable sort).
    order = np.lexsort((-dist, -lap.astype(np.int32)), axis=1).astype(np.int8)
    position = np.empty_like(lap)
    rows = np.arange(n)[:, None]
    position[rows, order] = np.arange(1, len(codes) + 1, dtype=np.int16)

    in_pit = np.zeros((n, len(codes)), dtype=np.bool_)
    for j, code in enumerate(codes):
        for start, end in pit_windows.get(code, []):
            in_pit[:, j] |= (timeline >= start) & (timeline <= end)

    columns = {
        "x": stack("x").astype(np.float32),
        "y": stack("y").astype(np.float32),
        "dist": dist,
        "lap": lap,
        "rel_dist": np.round(stack("rel_dist"), 4).astype(np.float32),
        "tyre": stack("tyre").astype(np.float32),
        "tyre_life": stack("tyre_life").astype(np.float32),
        "position": position,
        "speed": stack("speed").astype(np.float32),
        # int() truncation, as in the original per-frame build
        "gear": np.trunc(stack("gear")).astype(np.int16),
        "drs": np.trunc(stack("drs")).astype(np.int16),
        "throttle": stack("throttle").astype(np.float32),
        "brake": stack("brake").astype(np.float32),
        "in_pit": in_pit,
    }

    leader_lap = lap[np.arange(n), order[:, 0]] if codes else np.ones(n, dtype=np.int16)

    weather = None
    if weather_resampled:
        weather = {k: np.asarray(v, dtype=np.float32) for k, v in weather_resampled.items() if v is not None}

    return FrameStore(
        t=np.round(np.asarray(timeline, dtype=np.float64), 3),
        leader_lap=leader_lap.astype(np.int16),
        codes=codes,
        order=order,
        columns=columns,
        weather=weather,
    )


def fallback_lap_times(frames, min_lap_time_s=30.0, max_lap_time_s=7200.0):
    """Lap times from lap-number changes, computed on the arrays.

    Same result as walking every frame dict: a lap ends the first time a
    driver's lap number exceeds the highest lap seen so far.
    """
    t = frames.t
    result = {}
    lap_cols = frames.columns["lap"]
    tyre_cols = frames.columns["tyre"]
    life_cols = frames.columns["tyre_life"]
    for j, code in enumerate(frames.codes):
        laps = lap_cols[:, j].astype(np.int64)
        entries = []
        result[code] = entries
        if len(laps) == 0:
            continue
        running = np.maximum.accumulate(laps)
        change = np.flatnonzero(laps[1:] > running[:-1]) + 1
        start_t = float(t[0])
        prev_lap = int(laps[0])
        for i in change.tolist():
            end_t = float(t[i])
            lap_time = end_t - start_t
            if min_lap_time_s < lap_time < max_lap_time_s and prev_lap >= 2:
                entries.append({
                    "lap": prev_lap,
                    "time_s": float(lap_time),
                    "end_time_s": end_t,
                    "tyre": int(round(float(tyre_cols[i, j]))),
                    "tyre_life": int(round(float(life_cols[i, j]))),
                    "start_time_s": start_t,
                })
            prev_lap = int(laps[i])
            start_t = end_t
    return result


def frame_store_from_dicts(frames):
    """Convert a list of frame dicts (old cache format) to a FrameStore."""
    n = len(frames)
    codes = list(frames[0]["drivers"].keys()) if n else []
    col = {c: j for j, c in enumerate(codes)}
    d = len(codes)
    columns = {name: np.zeros((n, d), dtype=dtype) for name, dtype in DRIVER_FIELDS}
    order = np.zeros((n, d), dtype=np.int8)
    t = np.zeros(n)
    leader_lap = np.ones(n, dtype=np.int16)
    has_weather = n > 0 and "weather" in frames[0]
    weather = {name: np.full(n, np.nan, dtype=np.float32) for name in WEATHER_FIELDS} if has_weather else None
    if has_weather:
        weather["rainfall"] = np.zeros(n, dtype=np.float32)
    has_sc = any("safety_car" in f for f in frames[:1])
    sc_active = np.zeros(n, dtype=np.bool_)
    sc_x = np.zeros(n)
    sc_y = np.zeros(n)
    sc_phase = np.zeros(n, dtype=np.int8)
    sc_alpha = np.zeros(n, dtype=np.float32)

    for i, frame in enumerate(frames):
        t[i] = frame.get("t", 0.0)
        leader_lap[i] = frame.get("lap", 1)
        for k, (code, drv) in enumerate(frame["drivers"].items()):
            j = col[code]
            order[i, k] = j
            for name, _ in DRIVER_FIELDS:
                columns[name][i, j] = drv.get(name, 0)
        if has_weather:
            w = frame.get("weather") or {}
            for name in WEATHER_FIELDS:
                if w.get(name) is not None:
                    weather[name][i] = w[name]
            weather["rainfall"][i] = 1.0 if w.get("rain_state") == "RAINING" else 0.0
        sc = frame.get("safety_car")
        if sc:
            has_sc = True
            sc_active[i] = True
            sc_x[i], sc_y[i] = sc["x"], sc["y"]
            sc_phase[i] = SC_PHASES.index(sc.get("phase", "on_track"))
            sc_alpha[i] = sc.get("alpha", 1.0)

    if weather is not None:
        # Fields that were never present stay missing (reported as None).
        weather = {k: v for k, v in weather.items() if k == "rainfall" or not np.isnan(v).all()}

    store = FrameStore(t, leader_lap, codes, order, columns, weather)
    if has_sc:
        store.set_safety_car_arrays(sc_active, sc_x, sc_y, sc_phase, sc_alpha)
    return store
