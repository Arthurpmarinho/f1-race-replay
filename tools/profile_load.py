"""Measure where loading a race spends its time, on real FastF1 data.

    python tools/profile_load.py --year 2024 --round 12

Prints, step by step:
  1. time to load the FastF1 session
  2. old ``lap.get_telemetry()`` vs the new ``lap_telemetry(lap)`` on a few
     drivers, and checks both give the same numbers
  3. the full first computation of the race (as with --refresh-data), and
     the time to read it back from the cache
  4. how long building one replay frame takes

Nothing in computed_data/ is deleted; step 3 rewrites the cache for the
chosen race, exactly like running the app with --refresh-data.
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

COLUMNS = ("SessionTime", "X", "Y", "Distance", "RelativeDistance", "Speed",
           "nGear", "DRS", "Throttle", "Brake")


def step(title):
    print(f"\n=== {title} ===", flush=True)


def compare_lap_methods(session, n_drivers):
    from src.lib.lap_telemetry import lap_telemetry

    old_total = new_total = 0.0
    laps_done = 0
    worst = 0.0
    for drv in list(session.drivers)[:n_drivers]:
        for _, lap in session.laps.pick_drivers(drv).iterlaps():
            try:
                t0 = time.perf_counter()
                old = lap.get_telemetry()
                t1 = time.perf_counter()
                new = lap_telemetry(lap)
                t2 = time.perf_counter()
            except KeyError:
                continue  # lap without position data, the app skips it too
            old_total += t1 - t0
            new_total += t2 - t1
            laps_done += 1
            if len(old) != len(new):
                print(f"  DIFF: driver {drv} lap {lap.LapNumber}: {len(old)} vs {len(new)} rows")
                worst = float("inf")
                continue
            for col in COLUMNS:
                a, b = old[col], new[col]
                if col == "SessionTime":
                    a, b = a.dt.total_seconds(), b.dt.total_seconds()
                a = np.asarray(a, dtype=float)
                b = np.asarray(b, dtype=float)
                diff = np.nanmax(np.abs(a - b)) if len(a) else 0.0
                worst = max(worst, float(diff))
    print(f"  {laps_done} laps from {n_drivers} drivers")
    print(f"  lap.get_telemetry():  {old_total:7.2f}s  ({1000 * old_total / max(laps_done, 1):.0f} ms/lap)")
    print(f"  lap_telemetry(lap):   {new_total:7.2f}s  ({1000 * new_total / max(laps_done, 1):.0f} ms/lap)")
    print(f"  speed-up: {old_total / max(new_total, 1e-9):.1f}x")
    print(f"  largest difference in any column: {worst:g}  ({'OK' if worst < 1e-6 else 'CHECK'})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--round", type=int, default=12)
    parser.add_argument("--sprint", action="store_true")
    parser.add_argument("--compare-drivers", type=int, default=3,
                        help="drivers used for the old vs new comparison (0 to skip)")
    args = parser.parse_args()
    session_type = "S" if args.sprint else "R"

    from src.f1_data import enable_cache, get_race_telemetry, load_session

    enable_cache()

    step("1. Loading the FastF1 session (with telemetry)")
    t0 = time.perf_counter()
    session = load_session(args.year, args.round, session_type)
    if session is None:
        sys.exit("Could not load the session (check the year/round and your internet connection).")
    print(f"  {time.perf_counter() - t0:.1f}s")

    if args.compare_drivers:
        step("2. Old vs new per-lap telemetry")
        compare_lap_methods(session, args.compare_drivers)

    step("3. First computation of the race (like --refresh-data)")
    sys.argv.append("--refresh-data")
    t0 = time.perf_counter()
    data = get_race_telemetry(session, session_type)
    print(f"  computed in {time.perf_counter() - t0:.1f}s")
    sys.argv.remove("--refresh-data")
    t0 = time.perf_counter()
    data = get_race_telemetry(session, session_type)
    print(f"  read back from cache in {time.perf_counter() - t0:.1f}s")

    step("4. Building replay frames")
    frames = data["frames"]
    idx = np.linspace(0, len(frames) - 1, 2000).astype(int)
    t0 = time.perf_counter()
    for i in idx:
        frames[int(i)]
    per = (time.perf_counter() - t0) / len(idx)
    print(f"  {len(frames)} frames, {per * 1e6:.0f} us per frame")

    print(f"\nPython {sys.version.split()[0]}, {os.cpu_count()} CPU cores")


if __name__ == "__main__":
    main()
