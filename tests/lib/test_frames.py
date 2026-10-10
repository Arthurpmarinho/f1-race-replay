import pickle

import numpy as np

from src.lib.frames import (
    FrameStore,
    build_frame_store,
    fallback_lap_times,
    frame_store_from_dicts,
    frames_have_weather,
)


def _resampled(n=300):
    t = np.arange(n) / 25.0
    data = {}
    for k, code in enumerate(["AAA", "BBB", "CCC"]):
        dist = t * (60.0 + k) + 5 * k
        lap = np.floor(dist / 100.0) + 1
        data[code] = {
            "t": t, "x": dist, "y": -dist, "dist": dist, "rel_dist": (dist % 100) / 100,
            "lap": lap, "tyre": np.full(n, 1.0), "tyre_life": lap,
            "speed": np.full(n, 200.0), "gear": np.full(n, 7.6), "drs": np.zeros(n),
            "throttle": np.full(n, 100.0), "brake": np.zeros(n),
        }
    pit = {"BBB": [(2.0, 4.0)]}
    weather = {"track_temp": np.full(n, 40.0), "air_temp": np.full(n, 25.0),
               "humidity": None, "rainfall": np.zeros(n)}
    return t, data, pit, weather


def test_frame_dict_shape_and_positions():
    t, data, pit, weather = _resampled()
    store = build_frame_store(t, data, pit, weather)

    assert len(store) == len(t)
    frame = store[100]
    assert frame["t"] == round(float(t[100]), 3)
    # CCC is fastest and starts furthest ahead, so it leads.
    assert list(frame["drivers"]) == ["CCC", "BBB", "AAA"]
    assert [d["position"] for d in frame["drivers"].values()] == [1, 2, 3]
    assert frame["lap"] == frame["drivers"]["CCC"]["lap"]
    assert frame["drivers"]["AAA"]["gear"] == 7
    assert frame["weather"]["humidity"] is None
    assert frame["weather"]["rain_state"] == "DRY"
    assert "safety_car" not in frame


def test_in_pit_window():
    t, data, pit, weather = _resampled()
    store = build_frame_store(t, data, pit, weather)
    assert store[75]["drivers"]["BBB"]["in_pit"] is True   # t = 3.0s
    assert store[150]["drivers"]["BBB"]["in_pit"] is False  # t = 6.0s
    assert store[75]["drivers"]["AAA"]["in_pit"] is False


def test_sequence_protocol_and_pickle():
    t, data, pit, weather = _resampled()
    store = build_frame_store(t, data, pit, weather)
    assert store[-1]["t"] == store[len(store) - 1]["t"]
    assert [f["t"] for f in store[:3]] == [f["t"] for f in list(store)[:3]]
    assert frames_have_weather(store)

    restored = pickle.loads(pickle.dumps(store))
    assert isinstance(restored, FrameStore)
    assert restored[42] == store[42]


def test_round_trip_from_old_dict_format():
    t, data, pit, weather = _resampled()
    store = build_frame_store(t, data, pit, weather)
    old_frames = [store._build(i) for i in range(len(store))]
    converted = frame_store_from_dicts(old_frames)
    for i in (0, 50, 299):
        assert converted[i] == store[i]


def test_fallback_lap_times_matches_frame_walk():
    t, data, pit, weather = _resampled(n=2000)
    store = build_frame_store(t, data, pit, weather)
    fast = fallback_lap_times(store, min_lap_time_s=0.5)

    # Reference implementation: walk the frame dicts.
    expected = {}
    current, start = {}, {}
    for frame in store:
        for code, drv in frame["drivers"].items():
            lap = drv["lap"]
            if code not in current:
                current[code], start[code] = lap, frame["t"]
                expected.setdefault(code, [])
                continue
            if lap > current[code]:
                lap_time = frame["t"] - start[code]
                if 0.5 < lap_time < 7200 and current[code] >= 2:
                    expected[code].append((current[code], lap_time))
                current[code], start[code] = lap, frame["t"]

    for code, entries in expected.items():
        got = [(e["lap"], e["time_s"]) for e in fast[code]]
        assert len(got) == len(entries) > 0
        for (lap_a, time_a), (lap_b, time_b) in zip(got, entries):
            assert lap_a == lap_b
            assert abs(time_a - time_b) < 1e-9
