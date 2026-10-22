"""History analytics end to end, with Open-Meteo mocked: correct answers AND as few calls as possible."""
import threading
import time
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest
import respx
from sqlalchemy import update

from app.core.config import get_settings
from app.models import City, ClimateNormal, DailyWeather
from app.services.openmeteo import ARCHIVE_URL, FINAL_AFTER_DAYS
from tests.conftest import register


class FakeArchive:
    """Answers like Open-Meteo's archive for any date range, and remembers what was asked."""

    def __init__(self):
        self.requests: list[tuple[date, date]] = []
        self.offset = 3600              # the city's UTC offset (Paris in winter)
        self.null_dates: set[date] = set()
        self.fail_normals = False
        self.fail_all = False
        self.fail_latitudes: set[str] = set()   # e.g. {"41.89"}: requests for that latitude fail
        self.delay = 0.0                         # seconds per request, to test parallel loading
        self._lock = threading.Lock()
        self.in_flight = 0
        self.max_in_flight = 0

    @staticmethod
    def tmean(day: date) -> float:
        return 10.0 + day.toordinal() % 10

    def __call__(self, request: httpx.Request) -> httpx.Response:
        with self._lock:
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            time.sleep(self.delay)
            return self._answer(request)
        finally:
            with self._lock:
                self.in_flight -= 1

    def _answer(self, request: httpx.Request) -> httpx.Response:
        if any(request.url.params["latitude"].startswith(lat) for lat in self.fail_latitudes):
            return httpx.Response(500)
        start = date.fromisoformat(request.url.params["start_date"])
        end = date.fromisoformat(request.url.params["end_date"])
        self.requests.append((start, end))
        if self.fail_all or (self.fail_normals and start.year == 1991):
            return httpx.Response(500)
        days = [start + timedelta(days=i) for i in range((end - start).days + 1)]

        def column(value):
            return [None if d in self.null_dates else value(d) for d in days]

        return httpx.Response(200, json={
            "utc_offset_seconds": self.offset,
            "daily": {
                "time": [d.isoformat() for d in days],
                "temperature_2m_mean": column(self.tmean),
                "temperature_2m_min": column(lambda d: self.tmean(d) - 4),
                "temperature_2m_max": column(lambda d: self.tmean(d) + 4),
                "relative_humidity_2m_mean": column(lambda d: 70.0),
                "precipitation_sum": column(lambda d: 1.5 if d.toordinal() % 3 == 0 else 0.0),
                "wind_speed_10m_max": column(lambda d: 5.0),
            },
        })

    @property
    def period_requests(self):
        return [r for r in self.requests if r[0].year != 1991]

    @property
    def normals_requests(self):
        return [r for r in self.requests if r[0].year == 1991]


@pytest.fixture
def archive():
    fake = FakeArchive()
    with respx.mock(assert_all_called=False) as router:
        router.get(ARCHIVE_URL).mock(side_effect=fake)
        yield fake


@pytest.fixture
def user(client):
    register(client)
    return client


@pytest.fixture
def paris(db) -> int:
    city = City(name="Paris", state="Ile-de-France", country="FR", lat=48.8534, lon=2.3488)
    db.add(city)
    db.commit()
    return city.id


def local_yesterday(offset_s: int) -> date:
    return (datetime.now(UTC) + timedelta(seconds=offset_s)).date() - timedelta(days=1)


# --- one city -------------------------------------------------------------------------------

def test_first_visit_fetches_the_period_and_the_normals_once(user, paris, archive):
    body = user.get(f"/api/cities/{paris}/analytics", params={"days": 30}).json()
    yesterday = local_yesterday(archive.offset)
    assert len(body["daily"]) == 30
    assert body["period"] == {"start": (yesterday - timedelta(days=29)).isoformat(), "end": yesterday.isoformat(), "days": 30}
    assert body["normals"] == {"available": True, "baseline": "1991-2020"}
    assert body["summary"]["coverage"] == 1.0 and body["summary"]["missing_dates"] == []
    assert archive.normals_requests == [(date(1991, 1, 1), date(2020, 12, 31))]
    # one request for the period, including the 6 extra days the 7-day rolling mean needs
    assert len(archive.period_requests) == 1
    assert body["daily"][0]["tmean_7d"] is not None


def test_values_and_normals_are_correct(user, paris, archive):
    day = user.get(f"/api/cities/{paris}/analytics", params={"days": 30}).json()["daily"][-1]
    when = date.fromisoformat(day["date"])
    assert day["tmean"] == FakeArchive.tmean(when)
    assert day["tmin"] == day["tmean"] - 4 and day["tmax"] == day["tmean"] + 4
    assert day["normal_tmean"] is not None
    assert day["anomaly"] == pytest.approx(day["tmean"] - day["normal_tmean"], abs=0.01)
    assert day["category"] in {"warm", "cool", "normal"}


def test_second_visit_makes_no_calls(user, paris, archive):
    user.get(f"/api/cities/{paris}/analytics", params={"days": 30})
    calls = len(archive.requests)
    again = user.get(f"/api/cities/{paris}/analytics", params={"days": 30}).json()
    assert len(archive.requests) == calls              # days and normals both come from the database
    assert again["normals"]["available"] is True


def test_normals_are_never_refetched(user, paris, archive, db):
    user.get(f"/api/cities/{paris}/analytics")
    db.execute(update(ClimateNormal).values(computed_at=datetime.now(UTC) - timedelta(days=3650)))
    db.commit()
    user.get(f"/api/cities/{paris}/analytics", params={"days": 90})
    assert len(archive.normals_requests) == 1


def test_only_recent_days_are_refreshed_and_only_when_due(user, paris, archive, db):
    user.get(f"/api/cities/{paris}/analytics", params={"days": 30})
    # everything was fetched 7 hours ago
    db.execute(update(DailyWeather).values(fetched_at=datetime.now(UTC) - timedelta(hours=7)))
    db.commit()
    user.get(f"/api/cities/{paris}/analytics", params={"days": 30})
    start, end = archive.period_requests[-1]
    yesterday = local_yesterday(archive.offset)
    assert end == yesterday
    assert start >= yesterday - timedelta(days=FINAL_AFTER_DAYS)   # only the last week, not all 36 days


def test_final_days_are_never_fetched_again(user, paris, archive, db):
    user.get(f"/api/cities/{paris}/analytics", params={"days": 30})
    db.execute(update(DailyWeather).where(DailyWeather.is_final.is_(True))
               .values(fetched_at=datetime.now(UTC) - timedelta(days=400)))
    db.commit()
    calls = len(archive.requests)
    user.get(f"/api/cities/{paris}/analytics", params={"days": 30})
    assert len(archive.requests) == calls


def test_a_longer_period_only_fetches_the_older_missing_days(user, paris, archive):
    user.get(f"/api/cities/{paris}/analytics", params={"days": 30})
    first_start = archive.period_requests[0][0]
    user.get(f"/api/cities/{paris}/analytics", params={"days": 90})
    start, end = archive.period_requests[-1]
    assert end == first_start - timedelta(days=1)                   # stops where the stored days begin


def test_missing_values_stay_missing(user, paris, archive, db):
    yesterday = local_yesterday(archive.offset)
    archive.null_dates = {yesterday - timedelta(days=3), yesterday - timedelta(days=10)}
    body = user.get(f"/api/cities/{paris}/analytics", params={"days": 30}).json()
    by_date = {d["date"]: d for d in body["daily"]}
    gap = by_date[(yesterday - timedelta(days=3)).isoformat()]
    assert gap["tmean"] is None and gap["precip"] is None and gap["anomaly"] is None and gap["category"] is None
    assert body["summary"]["days_with_data"] == 28
    assert sorted(body["summary"]["missing_dates"]) == sorted(d.isoformat() for d in archive.null_dates)
    stored = db.query(DailyWeather).filter(DailyWeather.date == yesterday - timedelta(days=3)).one()
    assert stored.tmean is None and stored.precip is None             # NULL, never 0


def test_today_is_never_stored(user, paris, archive, db):
    user.get(f"/api/cities/{paris}/analytics")
    today_local = local_yesterday(archive.offset) + timedelta(days=1)
    assert db.query(DailyWeather).filter(DailyWeather.date >= today_local).count() == 0


def test_the_city_utc_offset_decides_which_day_is_yesterday(user, paris, archive, db):
    archive.offset = 14 * 3600                                       # Kiribati: already "tomorrow"
    user.get(f"/api/cities/{paris}/analytics")
    assert db.get(City, paris).utc_offset_s == 14 * 3600
    body = user.get(f"/api/cities/{paris}/analytics").json()
    assert body["period"]["end"] == local_yesterday(14 * 3600).isoformat()


def test_normals_failure_still_gives_analytics_and_retries_next_time(user, paris, archive):
    archive.fail_normals = True
    body = user.get(f"/api/cities/{paris}/analytics").json()
    assert body["normals"]["available"] is False
    assert body["daily"][0]["normal_tmean"] is None and body["summary"]["tmean_avg"] is not None
    archive.fail_normals = False
    assert user.get(f"/api/cities/{paris}/analytics").json()["normals"]["available"] is True
    assert len(archive.normals_requests) == 2


def test_open_meteo_down(user, paris, archive, db):
    archive.fail_all = True
    response = user.get(f"/api/cities/{paris}/analytics")
    assert response.status_code == 503                               # nothing stored yet
    archive.fail_all = False
    user.get(f"/api/cities/{paris}/analytics")
    db.execute(update(DailyWeather).values(fetched_at=datetime.now(UTC) - timedelta(hours=7)))
    db.commit()
    archive.fail_all = True
    body = user.get(f"/api/cities/{paris}/analytics").json()
    assert body["stale"] is True and len(body["daily"]) == 30        # what we have, marked stale


@pytest.mark.parametrize("days", [0, 7, 45, 1000])
def test_only_30_90_or_365_days(user, paris, days):
    assert user.get(f"/api/cities/{paris}/analytics", params={"days": days}).status_code == 422


def test_unknown_city(user, archive):
    assert user.get("/api/cities/999999/analytics").status_code == 404


# --- compare -------------------------------------------------------------------------------

@pytest.fixture
def three_cities(db, paris) -> list[int]:
    others = [City(name="Rome", country="IT", lat=41.8933, lon=12.4829), City(name="Oslo", country="NO", lat=59.9133, lon=10.7389)]
    db.add_all(others)
    db.commit()
    return [paris, others[0].id, others[1].id]


def test_compare_two_or_three_cities(user, three_cities, archive):
    body = user.get("/api/analytics/compare", params={"city_id": three_cities, "days": 30}).json()
    assert [c["city"]["name"] for c in body["cities"]] == ["Paris", "Rome", "Oslo"]
    assert len(body["dates"]) == 30
    for city in body["cities"]:
        assert len(city["series"]["tmean"]) == 30 and len(city["series"]["tmean_7d"]) == 30
        assert city["normals_available"] is True and city["summary"]["coverage"] == 1.0


@pytest.mark.parametrize("pick", ["one", "same twice", "four"])
def test_compare_needs_2_or_3_different_cities(user, three_cities, archive, db, pick):
    fourth = City(name="Lima", country="PE", lat=-12.0432, lon=-77.0282)
    db.add(fourth)
    db.commit()
    city_ids = {"one": three_cities[:1], "same twice": [three_cities[0]] * 2, "four": [*three_cities, fourth.id]}[pick]
    response = user.get("/api/analytics/compare", params={"city_id": city_ids})
    assert response.status_code == 422 and "2 or 3" in response.json()["detail"]


def test_compare_unknown_city(user, three_cities, archive):
    assert user.get("/api/analytics/compare", params={"city_id": [three_cities[0], 999999]}).status_code == 404


def test_compare_loads_cities_in_parallel(user, three_cities, archive, db):
    # Warm up: the normals get computed once (CPU work, which threads can't overlap anyway)
    user.get("/api/analytics/compare", params={"city_id": three_cities, "days": 30})
    db.query(DailyWeather).delete()
    db.commit()
    archive.delay, archive.max_in_flight = 0.6, 0
    started = time.perf_counter()
    body = user.get("/api/analytics/compare", params={"city_id": three_cities, "days": 30}).json()
    elapsed = time.perf_counter() - started
    assert [c["city"]["name"] for c in body["cities"]] == ["Paris", "Rome", "Oslo"]   # order kept
    assert archive.max_in_flight == 3                        # all three cities at the same time
    assert elapsed < 3 * 0.6                                 # one after another would take at least 1.8 s


def test_compare_with_one_city_down_and_nothing_stored(user, three_cities, archive):
    archive.fail_latitudes = {"41.89"}                       # Rome
    response = user.get("/api/analytics/compare", params={"city_id": three_cities})
    assert response.status_code == 503                       # no history for Rome at all: can't compare honestly
