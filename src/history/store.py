"""
Local cache of historical F1 data from Jolpica.

Each dataset is stored as JSON under <computed_data>/history/<season>/. A past
season is fetched once and then read from disk; the season in progress is
refetched once its copy is older than `max_age_hours`. Lap times and pit stops
are large (around 15 requests per race), so they are only fetched per race on
request rather than as part of a season sync.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import pandas as pd

from src.history import jolpica
from src.history.jolpica import FIRST_SEASON, JolpicaClient

SEASON_DATASETS = {
    "schedule": ("races", jolpica.flatten_schedule),
    "results": ("results", jolpica.flatten_results),
    "qualifying": ("qualifying", jolpica.flatten_qualifying),
    "sprint": ("sprint", jolpica.flatten_sprint),
    "driver_standings": ("driverstandings", jolpica.flatten_driver_standings),
    "constructor_standings": ("constructorstandings", jolpica.flatten_constructor_standings),
}

RACE_DATASETS = {
    "lap_times": ("laps", jolpica.flatten_lap_times),
    "pit_stops": ("pitstops", jolpica.flatten_pit_stops),
}


def default_history_dir() -> Path:
    from src.lib.settings import get_settings

    return Path(get_settings().computed_data_location) / "history"


class HistoryStore:
    def __init__(
        self,
        root: str | os.PathLike | None = None,
        client: JolpicaClient | None = None,
        max_age_hours: float = 6.0,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ):
        self.root = Path(root) if root is not None else default_history_dir()
        self.client = client or JolpicaClient()
        self.max_age_hours = max_age_hours
        self._now = now

    # Paths and cache bookkeeping

    def _path(self, season: int, name: str) -> Path:
        return self.root / str(season) / f"{name}.json"

    def _is_final(self, season: int) -> bool:
        return season < self._now().year

    def _read(self, path: Path) -> dict | None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def _is_fresh(self, cached: dict, season: int) -> bool:
        if cached.get("final"):
            return True
        try:
            fetched = datetime.fromisoformat(cached["fetched_at"])
        except (KeyError, ValueError):
            return False
        return (self._now() - fetched).total_seconds() < self.max_age_hours * 3600

    def _write(self, path: Path, season: int, rows: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "fetched_at": self._now().isoformat(),
            "final": self._is_final(season),
            "rows": rows,
        }
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        os.replace(tmp, path)

    def _load(self, season: int, dataset: str, name: str, api_path: str, flatten, refresh: bool) -> pd.DataFrame:
        if season < FIRST_SEASON[dataset]:
            return pd.DataFrame()

        path = self._path(season, name)
        cached = None if refresh else self._read(path)
        if cached is not None and self._is_fresh(cached, season):
            return pd.DataFrame(cached["rows"])

        try:
            rows = self.client.fetch_rows(api_path, flatten)
        except jolpica.JolpicaError:
            # Offline or rate limited: an old copy is better than nothing.
            if cached is not None:
                return pd.DataFrame(cached["rows"])
            raise
        self._write(path, season, rows)
        return pd.DataFrame(rows)

    def is_cached(self, season: int, dataset: str, round_no: int | None = None) -> bool:
        name = dataset if round_no is None else f"round_{round_no:02d}_{dataset}"
        return self._path(season, name).exists()

    def cached_seasons(self) -> list[int]:
        if not self.root.exists():
            return []
        return sorted(int(p.name) for p in self.root.iterdir() if p.is_dir() and p.name.isdigit())

    # Season-level data

    def season(self, season: int, dataset: str, refresh: bool = False) -> pd.DataFrame:
        endpoint, flatten = SEASON_DATASETS[dataset]
        return self._load(season, dataset, dataset, f"{season}/{endpoint}", flatten, refresh)

    def schedule(self, season: int, refresh: bool = False) -> pd.DataFrame:
        return self.season(season, "schedule", refresh)

    def results(self, season: int, refresh: bool = False) -> pd.DataFrame:
        return self.season(season, "results", refresh)

    def qualifying(self, season: int, refresh: bool = False) -> pd.DataFrame:
        return self.season(season, "qualifying", refresh)

    def sprint(self, season: int, refresh: bool = False) -> pd.DataFrame:
        return self.season(season, "sprint", refresh)

    def driver_standings(self, season: int, refresh: bool = False) -> pd.DataFrame:
        return self.season(season, "driver_standings", refresh)

    def constructor_standings(self, season: int, refresh: bool = False) -> pd.DataFrame:
        return self.season(season, "constructor_standings", refresh)

    def sync_season(self, season: int, refresh: bool = False) -> dict[str, int]:
        """Fetch every season-level dataset. Returns row counts per dataset."""
        return {name: len(self.season(season, name, refresh)) for name in SEASON_DATASETS}

    # Race-level data

    def race(self, season: int, round_no: int, dataset: str, refresh: bool = False) -> pd.DataFrame:
        endpoint, flatten = RACE_DATASETS[dataset]
        name = f"round_{round_no:02d}_{dataset}"
        return self._load(season, dataset, name, f"{season}/{round_no}/{endpoint}", flatten, refresh)

    def lap_times(self, season: int, round_no: int, refresh: bool = False) -> pd.DataFrame:
        return self.race(season, round_no, "lap_times", refresh)

    def pit_stops(self, season: int, round_no: int, refresh: bool = False) -> pd.DataFrame:
        return self.race(season, round_no, "pit_stops", refresh)

    # Multi-season helpers, mainly for modelling

    def results_range(self, first: int, last: int, dataset: str = "results") -> pd.DataFrame:
        frames = [self.season(s, dataset) for s in range(first, last + 1)]
        frames = [f for f in frames if not f.empty]
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
