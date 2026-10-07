from datetime import datetime, timedelta, timezone

import pytest

from src.history.jolpica import JolpicaError
from src.history.store import HistoryStore


class FakeClient:
    def __init__(self, rows=None, error=None):
        self.rows = rows if rows is not None else [{"season": 1950, "round": 1, "position": 1}]
        self.error = error
        self.paths = []
        self.request_count = 0

    def fetch_rows(self, path, flatten):
        self.paths.append(path)
        if self.error:
            raise self.error
        return list(self.rows)


class Clock:
    def __init__(self, when):
        self.when = when

    def __call__(self):
        return self.when


def make_store(tmp_path, client=None, when=datetime(2026, 10, 7, tzinfo=timezone.utc)):
    clock = Clock(when)
    return HistoryStore(root=tmp_path, client=client or FakeClient(), now=clock), clock


def test_past_season_is_fetched_once(tmp_path):
    store, clock = make_store(tmp_path)
    assert len(store.results(1950)) == 1
    clock.when += timedelta(days=400)
    assert len(store.results(1950)) == 1
    assert store.client.paths == ["1950/results"]
    assert (tmp_path / "1950" / "results.json").exists()
    assert store.cached_seasons() == [1950]


def test_current_season_is_refetched_when_stale(tmp_path):
    store, clock = make_store(tmp_path)
    store.results(2026)
    clock.when += timedelta(hours=1)
    store.results(2026)
    assert len(store.client.paths) == 1
    clock.when += timedelta(hours=7)
    store.results(2026)
    assert len(store.client.paths) == 2


def test_refresh_forces_download(tmp_path):
    store, _ = make_store(tmp_path)
    store.results(1950)
    store.results(1950, refresh=True)
    assert len(store.client.paths) == 2


def test_datasets_before_their_first_season_cost_no_requests(tmp_path):
    store, _ = make_store(tmp_path)
    assert store.qualifying(1960).empty
    assert store.sprint(2019).empty
    assert store.constructor_standings(1955).empty
    assert store.lap_times(1990, 3).empty
    assert store.pit_stops(2005, 3).empty
    assert store.client.paths == []


def test_race_level_paths(tmp_path):
    store, _ = make_store(tmp_path)
    store.lap_times(2011, 4)
    store.pit_stops(2011, 4)
    assert store.client.paths == ["2011/4/laps", "2011/4/pitstops"]
    assert store.is_cached(2011, "lap_times", 4)


def test_stale_copy_is_used_when_offline(tmp_path):
    store, clock = make_store(tmp_path)
    store.results(2026)
    clock.when += timedelta(days=1)
    store.client.error = JolpicaError("offline")
    assert len(store.results(2026)) == 1


def test_error_without_cache_propagates(tmp_path):
    store, _ = make_store(tmp_path, client=FakeClient(error=JolpicaError("offline")))
    with pytest.raises(JolpicaError):
        store.results(1950)


def test_sync_and_range(tmp_path):
    store, _ = make_store(tmp_path)
    counts = store.sync_season(1950)
    assert counts["results"] == 1 and counts["qualifying"] == 0 and counts["constructor_standings"] == 0
    assert sorted(store.client.paths) == ["1950/driverstandings", "1950/races", "1950/results"]
    store.results(1951)
    assert len(store.results_range(1950, 1951)) == 2
