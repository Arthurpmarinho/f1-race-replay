import pytest

from src.history import jolpica
from src.history.jolpica import JolpicaClient, JolpicaError, lap_time_to_seconds
from tests.history.fixtures import mrdata, race, result


class FakeResponse:
    def __init__(self, payload=None, status=200, headers=None):
        self._payload = payload
        self.status_code = status
        self.headers = headers or {}

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, dict(params)))
        return self.responses.pop(0)


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def make_client(responses, **kwargs):
    clock = FakeClock()
    session = FakeSession(responses)
    client = JolpicaClient(session=session, sleep=clock.sleep, clock=clock, **kwargs)
    return client, session, clock


def test_pages_until_total_and_merges_split_race():
    farina = result(1, "farina", "Nino", "Farina", "Alfa Romeo", 9, 1, fastest_rank=1)
    fagioli = result(2, "fagioli", "Luigi", "Fagioli", "Alfa Romeo", 6, 2)
    # The race is split across two pages, as happens when results cross the page size.
    page1 = mrdata(2, 0, 1, RaceTable={"Races": [race(1, Results=[farina])]})
    page2 = mrdata(2, 1, 1, RaceTable={"Races": [race(1, Results=[fagioli])]})
    client, session, _ = make_client([FakeResponse(page1), FakeResponse(page2)])

    rows = client.fetch_rows("1950/results", jolpica.flatten_results)

    assert [r["driver_id"] for r in rows] == ["farina", "fagioli"]
    assert [c[1]["offset"] for c in session.calls] == [0, 1]
    assert session.calls[0][0] == "https://api.jolpi.ca/ergast/f1/1950/results/"
    first = rows[0]
    assert first["season"] == 1950 and first["round"] == 1
    assert first["driver_name"] == "Nino Farina"
    assert first["points"] == 9.0 and first["grid"] == 1
    assert first["fastest_lap_rank"] == 1 and first["fastest_lap_time"] == "1:50.6"
    assert rows[1]["fastest_lap_rank"] is None


def test_retries_after_429_using_retry_after():
    ok = mrdata(0, 0, 100, RaceTable={"Races": []})
    client, session, clock = make_client([FakeResponse(status=429, headers={"Retry-After": "7"}), FakeResponse(ok)])

    assert client.fetch_rows("1950/results", jolpica.flatten_results) == []
    assert len(session.calls) == 2
    assert 7 in clock.sleeps


def test_gives_up_after_max_retries():
    client, _, _ = make_client([FakeResponse(status=503)] * 3, max_retries=2)
    with pytest.raises(JolpicaError):
        client.get_page("1950/results")


def test_client_error_is_not_retried():
    client, session, _ = make_client([FakeResponse(status=404)])
    with pytest.raises(JolpicaError):
        client.get_page("1950/nothing")
    assert len(session.calls) == 1


def test_throttle_spaces_requests_and_respects_hourly_budget():
    client, _, clock = make_client([], min_interval=0.5, hourly_limit=3)
    for _ in range(3):
        client._throttle()
    assert clock.sleeps == [0.5, 0.5]

    client._throttle()  # fourth call in the same hour has to wait for the first to expire
    assert clock.sleeps[-1] > 3500
    assert clock.now >= 3600


def test_lap_time_to_seconds():
    assert lap_time_to_seconds("1:23.456") == pytest.approx(83.456)
    assert lap_time_to_seconds("23.456") == pytest.approx(23.456)
    assert lap_time_to_seconds("") is None
    assert lap_time_to_seconds("n/a") is None


def test_flatten_laps_and_pit_stops():
    laps = mrdata(2, 0, 100, RaceTable={"Races": [race(1, season="2011", Laps=[
        {"number": "1", "Timings": [
            {"driverId": "vettel", "position": "1", "time": "1:35.123"},
            {"driverId": "webber", "position": "2", "time": "1:36.000"},
        ]},
    ])]})["MRData"]
    rows = jolpica.flatten_lap_times(laps)
    assert rows[0] == {"season": 2011, "round": 1, "lap": 1, "driver_id": "vettel",
                       "position": 1, "time": "1:35.123", "time_s": pytest.approx(95.123)}

    pits = mrdata(1, 0, 100, RaceTable={"Races": [race(1, season="2011", PitStops=[
        {"driverId": "vettel", "lap": "14", "stop": "1", "time": "17:28:24", "duration": "22.191"},
    ])]})["MRData"]
    stop = jolpica.flatten_pit_stops(pits)[0]
    assert stop["lap"] == 14 and stop["duration_s"] == pytest.approx(22.191)


def test_flatten_standings():
    data = mrdata(1, 0, 100, StandingsTable={"StandingsLists": [{
        "season": "1950", "round": "7",
        "DriverStandings": [{
            "position": "1", "points": "30", "wins": "3",
            "Driver": {"driverId": "farina", "givenName": "Nino", "familyName": "Farina"},
            "Constructors": [{"name": "Alfa Romeo"}],
        }],
    }]})["MRData"]
    row = jolpica.flatten_driver_standings(data)[0]
    assert (row["season"], row["round"], row["position"], row["points"], row["wins"]) == (1950, 7, 1, 30.0, 3)
    assert row["constructor_names"] == "Alfa Romeo"
