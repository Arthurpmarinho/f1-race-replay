"""
Command line access to the historical data cache.

    python -m src.history sync                    # every season from 1950 to now
    python -m src.history sync 1950 1979          # a range of seasons
    python -m src.history sync 2024 --laps        # also lap times and pit stops
    python -m src.history results 1950            # print a season's winners

Jolpica allows about 500 requests per hour. A full season sync costs roughly
10 requests, lap times about 15 per race, so a sync from 1950 takes a while
the first time; it can be stopped and resumed, cached seasons are skipped.
"""

import argparse
import sys

from src.history import FIRST_SEASON, HistoryStore, JolpicaError
from src.lib.season import get_season


def _sync(store: HistoryStore, first: int, last: int, laps: bool, refresh: bool) -> int:
    for season in range(first, last + 1):
        try:
            counts = store.sync_season(season, refresh=refresh)
            summary = ", ".join(f"{k} {v}" for k, v in counts.items() if v)
            print(f"{season}: {summary}  (requests so far: {store.client.request_count})")

            if laps:
                schedule = store.schedule(season)
                for round_no in schedule.get("round", []):
                    lap_rows = len(store.lap_times(season, int(round_no), refresh=refresh))
                    pit_rows = len(store.pit_stops(season, int(round_no), refresh=refresh))
                    print(f"  round {int(round_no)}: {lap_rows} lap times, {pit_rows} pit stops")
        except JolpicaError as exc:
            print(f"{season}: failed ({exc})", file=sys.stderr)
            return 1
    return 0


def _results(store: HistoryStore, season: int) -> int:
    results = store.results(season)
    if results.empty:
        print(f"No results for {season}")
        return 1
    winners = results[results["position"] == 1]
    for row in winners.itertuples():
        print(f"{row.round:>2}  {row.race_name:<32} {row.driver_name:<24} {row.constructor_name}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m src.history")
    sub = parser.add_subparsers(dest="command", required=True)

    sync = sub.add_parser("sync", help="download seasons into the local cache")
    sync.add_argument("first", type=int, nargs="?", help="first season (default: 1950)")
    sync.add_argument("last", type=int, nargs="?", help="last season (default: same as first, or the current season)")
    sync.add_argument("--laps", action="store_true", help="also fetch lap times and pit stops per race")
    sync.add_argument("--refresh", action="store_true", help="ignore the cache")

    res = sub.add_parser("results", help="print the winners of a season")
    res.add_argument("season", type=int)

    args = parser.parse_args(argv)
    store = HistoryStore()

    if args.command == "sync":
        if args.first is None:
            first, last = FIRST_SEASON["results"], get_season()
        else:
            first, last = args.first, args.last if args.last is not None else args.first
        return _sync(store, first, last, args.laps, args.refresh)
    return _results(store, args.season)


if __name__ == "__main__":
    sys.exit(main())
