"""
Small client for the Jolpica F1 API (the community successor of Ergast).

Jolpica serves results back to 1950. Its public limits are 4 requests per
second and 500 requests per hour, and a page holds at most 100 rows, so the
client paces itself and pages through every query. Each page is flattened into
plain row dicts right away, which means a race split across two pages needs no
special handling.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Callable, Iterable

import requests

BASE_URL = "https://api.jolpi.ca/ergast/f1"
PAGE_SIZE = 100

# First season each kind of data exists in the Ergast/Jolpica database.
FIRST_SEASON = {
    "schedule": 1950,
    "results": 1950,
    "driver_standings": 1950,
    "constructor_standings": 1958,  # constructors' championship started in 1958
    "qualifying": 1994,  # patchy until 2003
    "lap_times": 1996,
    "pit_stops": 2011,
    "sprint": 2021,
}


class JolpicaError(RuntimeError):
    pass


class JolpicaClient:
    def __init__(
        self,
        base_url: str = BASE_URL,
        session: requests.Session | None = None,
        min_interval: float = 0.3,
        hourly_limit: int = 480,
        max_retries: int = 4,
        timeout: float = 30.0,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.min_interval = min_interval
        self.hourly_limit = hourly_limit
        self.max_retries = max_retries
        self.timeout = timeout
        self._sleep = sleep
        self._clock = clock
        self._recent: deque[float] = deque()
        self._lock = threading.Lock()
        self.request_count = 0

    def _throttle(self) -> None:
        with self._lock:
            self._wait_for_slot()

    def _wait_for_slot(self) -> None:
        now = self._clock()
        while self._recent and now - self._recent[0] >= 3600:
            self._recent.popleft()

        if len(self._recent) >= self.hourly_limit:
            self._sleep(3600 - (now - self._recent[0]) + 1)
            now = self._clock()
            while self._recent and now - self._recent[0] >= 3600:
                self._recent.popleft()

        if self._recent:
            wait = self.min_interval - (now - self._recent[-1])
            if wait > 0:
                self._sleep(wait)
                now = self._clock()

        self._recent.append(now)

    def get_page(self, path: str, offset: int = 0, limit: int = PAGE_SIZE) -> dict:
        url = f"{self.base_url}/{path.strip('/')}/"
        params = {"limit": limit, "offset": offset}

        for attempt in range(self.max_retries + 1):
            self._throttle()
            self.request_count += 1
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                if attempt == self.max_retries:
                    raise JolpicaError(f"GET {url} failed: {exc}") from exc
                self._sleep(2 ** attempt)
                continue

            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt == self.max_retries:
                    raise JolpicaError(f"GET {url} returned {resp.status_code}")
                retry_after = resp.headers.get("Retry-After", "")
                self._sleep(float(retry_after) if retry_after.isdigit() else 2 ** (attempt + 1))
                continue

            if resp.status_code != 200:
                raise JolpicaError(f"GET {url} returned {resp.status_code}")

            try:
                return resp.json()["MRData"]
            except (ValueError, KeyError) as exc:
                raise JolpicaError(f"Unexpected response from {url}") from exc

        raise JolpicaError(f"GET {url} failed")

    def fetch_rows(self, path: str, flatten: Callable[[dict], Iterable[dict]]) -> list[dict]:
        """Fetch every page of `path` and return the flattened rows."""
        rows: list[dict] = []
        offset = 0
        while True:
            data = self.get_page(path, offset=offset)
            rows.extend(flatten(data))
            total = int(data.get("total", 0))
            limit = int(data.get("limit", PAGE_SIZE)) or PAGE_SIZE
            offset += limit
            if offset >= total:
                return rows


# Flatteners: one row per result, keyed with season/round so tables from
# different endpoints can be joined later.

def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def lap_time_to_seconds(text) -> float | None:
    """'1:23.456' -> 83.456, '23.456' -> 23.456, anything else -> None."""
    if not text:
        return None
    try:
        parts = str(text).split(":")
        seconds = 0.0
        for part in parts:
            seconds = seconds * 60 + float(part)
        return seconds
    except ValueError:
        return None


def _race_fields(race: dict) -> dict:
    circuit = race.get("Circuit", {})
    location = circuit.get("Location", {})
    return {
        "season": _int(race.get("season")),
        "round": _int(race.get("round")),
        "race_name": race.get("raceName"),
        "date": race.get("date"),
        "circuit_id": circuit.get("circuitId"),
        "circuit_name": circuit.get("circuitName"),
        "locality": location.get("locality"),
        "country": location.get("country"),
    }


def _driver_fields(driver: dict) -> dict:
    return {
        "driver_id": driver.get("driverId"),
        "driver_code": driver.get("code"),
        "driver_name": f"{driver.get('givenName', '')} {driver.get('familyName', '')}".strip(),
        "driver_nationality": driver.get("nationality"),
    }


def _constructor_fields(constructor: dict) -> dict:
    return {
        "constructor_id": constructor.get("constructorId"),
        "constructor_name": constructor.get("name"),
    }


def _races(data: dict) -> list[dict]:
    return data.get("RaceTable", {}).get("Races", [])


def flatten_schedule(data: dict) -> list[dict]:
    rows = []
    for race in _races(data):
        row = _race_fields(race)
        location = race.get("Circuit", {}).get("Location", {})
        row["time"] = race.get("time")
        row["lat"] = _float(location.get("lat"))
        row["long"] = _float(location.get("long"))
        rows.append(row)
    return rows


def _flatten_race_results(data: dict, key: str) -> list[dict]:
    rows = []
    for race in _races(data):
        base = _race_fields(race)
        for res in race.get(key, []):
            fastest = res.get("FastestLap", {})
            rows.append({
                **base,
                "position": _int(res.get("position")),
                "position_text": res.get("positionText"),
                "number": res.get("number"),
                **_driver_fields(res.get("Driver", {})),
                **_constructor_fields(res.get("Constructor", {})),
                "grid": _int(res.get("grid")),
                "laps": _int(res.get("laps")),
                "status": res.get("status"),
                "points": _float(res.get("points")),
                "time": res.get("Time", {}).get("time"),
                "time_millis": _int(res.get("Time", {}).get("millis")),
                "fastest_lap_rank": _int(fastest.get("rank")),
                "fastest_lap_number": _int(fastest.get("lap")),
                "fastest_lap_time": fastest.get("Time", {}).get("time"),
            })
    return rows


def flatten_results(data: dict) -> list[dict]:
    return _flatten_race_results(data, "Results")


def flatten_sprint(data: dict) -> list[dict]:
    return _flatten_race_results(data, "SprintResults")


def flatten_qualifying(data: dict) -> list[dict]:
    rows = []
    for race in _races(data):
        base = _race_fields(race)
        for res in race.get("QualifyingResults", []):
            rows.append({
                **base,
                "position": _int(res.get("position")),
                "number": res.get("number"),
                **_driver_fields(res.get("Driver", {})),
                **_constructor_fields(res.get("Constructor", {})),
                "q1": res.get("Q1"),
                "q2": res.get("Q2"),
                "q3": res.get("Q3"),
            })
    return rows


def _standings_lists(data: dict) -> list[dict]:
    return data.get("StandingsTable", {}).get("StandingsLists", [])


def flatten_driver_standings(data: dict) -> list[dict]:
    rows = []
    for standings in _standings_lists(data):
        for entry in standings.get("DriverStandings", []):
            constructors = entry.get("Constructors", [])
            rows.append({
                "season": _int(standings.get("season")),
                "round": _int(standings.get("round")),
                "position": _int(entry.get("position")),
                "points": _float(entry.get("points")),
                "wins": _int(entry.get("wins")),
                **_driver_fields(entry.get("Driver", {})),
                "constructor_names": ", ".join(c.get("name", "") for c in constructors),
            })
    return rows


def flatten_constructor_standings(data: dict) -> list[dict]:
    rows = []
    for standings in _standings_lists(data):
        for entry in standings.get("ConstructorStandings", []):
            rows.append({
                "season": _int(standings.get("season")),
                "round": _int(standings.get("round")),
                "position": _int(entry.get("position")),
                "points": _float(entry.get("points")),
                "wins": _int(entry.get("wins")),
                **_constructor_fields(entry.get("Constructor", {})),
            })
    return rows


def flatten_lap_times(data: dict) -> list[dict]:
    rows = []
    for race in _races(data):
        season, rnd = _int(race.get("season")), _int(race.get("round"))
        for lap in race.get("Laps", []):
            for timing in lap.get("Timings", []):
                rows.append({
                    "season": season,
                    "round": rnd,
                    "lap": _int(lap.get("number")),
                    "driver_id": timing.get("driverId"),
                    "position": _int(timing.get("position")),
                    "time": timing.get("time"),
                    "time_s": lap_time_to_seconds(timing.get("time")),
                })
    return rows


def flatten_pit_stops(data: dict) -> list[dict]:
    rows = []
    for race in _races(data):
        season, rnd = _int(race.get("season")), _int(race.get("round"))
        for stop in race.get("PitStops", []):
            rows.append({
                "season": season,
                "round": rnd,
                "driver_id": stop.get("driverId"),
                "lap": _int(stop.get("lap")),
                "stop": _int(stop.get("stop")),
                "time_of_day": stop.get("time"),
                "duration": stop.get("duration"),
                "duration_s": lap_time_to_seconds(stop.get("duration")),
            })
    return rows
