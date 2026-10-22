"""City search, current weather, forecast and caching, with OpenWeatherMap mocked by respx."""
import logging
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx
from sqlalchemy import select, update

from app.core.config import get_settings
from app.models import ApiCache, City, RecentSearch, WeatherSnapshot
from tests.conftest import register
from tests.owm_samples import current_answer, forecast_answer, geocode_answer

FAKE_KEY = "fake-owm-key-MUST-NEVER-LEAK-7f3a"
OWM = "https://api.openweathermap.org"


@pytest.fixture(autouse=True)
def owm(monkeypatch):
    monkeypatch.setenv("OPENWEATHER_API_KEY", FAKE_KEY)
    get_settings.cache_clear()
    with respx.mock(base_url=OWM, assert_all_called=False) as router:
        router.get("/geo/1.0/direct").respond(json=geocode_answer())
        router.get("/data/2.5/weather").respond(json=current_answer())
        router.get("/data/2.5/forecast").respond(json=forecast_answer())
        yield router
    get_settings.cache_clear()


@pytest.fixture
def user(client):
    register(client)
    return client


def london_id(client) -> int:
    return client.get("/api/cities/search", params={"q": "London"}).json()[0]["id"]


def calls(router, path: str) -> int:
    return sum(1 for call in router.calls if call.request.url.path == path)


# --- search ---------------------------------------------------------------------------

def test_search_returns_labelled_places_and_stores_them(user, db):
    results = user.get("/api/cities/search", params={"q": "London"}).json()
    assert [r["label"] for r in results] == ["London, England, GB", "London, Ontario, CA"]
    assert all(isinstance(r["id"], int) for r in results)
    assert db.query(City).count() == 2                         # duplicates from the API are dropped


def test_search_is_cached_and_spellings_share_the_cache(user, owm):
    first = user.get("/api/cities/search", params={"q": "London"}).json()
    again = user.get("/api/cities/search", params={"q": "  LONDON "}).json()
    assert first == again
    assert calls(owm, "/geo/1.0/direct") == 1                  # the second search didn't call the API


def test_search_validation_and_no_results(user, owm):
    assert user.get("/api/cities/search", params={"q": "L"}).status_code == 422
    owm.get("/geo/1.0/direct").respond(json=[])
    assert user.get("/api/cities/search", params={"q": "Qwzxv"}).json() == []


def test_search_sends_the_key_only_to_openweathermap(user, owm):
    user.get("/api/cities/search", params={"q": "London"})
    request = owm.calls.last.request
    assert request.url.params["appid"] == FAKE_KEY and request.url.params["q"] == "london"


# --- current weather ------------------------------------------------------------------

def test_current_weather(user):
    body = user.get(f"/api/cities/{london_id(user)}/weather").json()
    assert body["city"]["label"] == "London, England, GB"
    weather = body["weather"]
    assert weather["temp_c"] == 14.2 and weather["wind_deg"] == 230 and weather["theme"] == "rain"
    assert weather["timezone_offset_s"] == 3600 and weather["sunrise"] and weather["sunset"]
    assert body["stale"] is False


def test_opening_a_city_records_a_search_and_one_snapshot(user, db, owm):
    city_id = london_id(user)
    user.get(f"/api/cities/{city_id}/weather")
    user.get(f"/api/cities/{city_id}/weather")                  # same reading (cached): not stored twice
    assert db.query(RecentSearch).count() == 1
    assert db.query(WeatherSnapshot).count() == 1
    assert calls(owm, "/data/2.5/weather") == 1


def test_expired_cache_is_refreshed(user, db, owm):
    city_id = london_id(user)
    user.get(f"/api/cities/{city_id}/weather")
    db.execute(update(ApiCache).where(ApiCache.key.like("owm:current:%"))
               .values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
    db.commit()
    owm.get("/data/2.5/weather").respond(json=current_answer(dt=1_761_138_000, temp=16.0))
    body = user.get(f"/api/cities/{city_id}/weather").json()
    assert body["weather"]["temp_c"] == 16.0 and body["stale"] is False
    assert calls(owm, "/data/2.5/weather") == 2
    assert db.query(WeatherSnapshot).count() == 2               # a new reading


def test_api_down_serves_old_data_marked_stale(user, db, owm):
    city_id = london_id(user)
    user.get(f"/api/cities/{city_id}/weather")
    db.execute(update(ApiCache).values(expires_at=datetime.now(UTC) - timedelta(hours=1)))
    db.commit()
    owm.get("/data/2.5/weather").mock(side_effect=httpx.ConnectTimeout("timed out"))
    body = user.get(f"/api/cities/{city_id}/weather").json()
    assert body["stale"] is True and body["weather"]["temp_c"] == 14.2


@pytest.mark.parametrize("failure", [httpx.ConnectTimeout("t"), httpx.ConnectError("c")])
def test_api_down_without_cache_gives_a_friendly_503(user, owm, failure):
    city_id = london_id(user)
    owm.get("/data/2.5/weather").mock(side_effect=failure)
    response = user.get(f"/api/cities/{city_id}/weather")
    assert response.status_code == 503
    assert response.json() == {"detail": "The weather service is unavailable right now. Please try again in a minute."}


@pytest.mark.parametrize("status", [401, 429, 500, 502])
def test_api_errors_never_leak_the_key(user, owm, caplog, status):
    city_id = london_id(user)
    owm.get("/data/2.5/weather").respond(status, json={"cod": status, "message": f"Invalid API key {FAKE_KEY}"})
    with caplog.at_level(logging.DEBUG):
        response = user.get(f"/api/cities/{city_id}/weather")
    assert response.status_code == 503
    assert FAKE_KEY not in response.text and "API key" not in response.text
    assert FAKE_KEY not in caplog.text


def test_timeout_logs_no_url(user, owm, caplog):
    city_id = london_id(user)
    owm.get("/data/2.5/weather").mock(side_effect=httpx.ReadTimeout(f"timed out: {OWM}/data/2.5/weather?appid={FAKE_KEY}"))
    with caplog.at_level(logging.DEBUG):
        user.get(f"/api/cities/{city_id}/weather")
    assert FAKE_KEY not in caplog.text
    assert "timeout" in caplog.text


def test_missing_api_key(user, monkeypatch):
    city = london_id(user)
    monkeypatch.setenv("OPENWEATHER_API_KEY", "")     # empty also overrides a key in your local .env
    get_settings.cache_clear()
    response = user.get(f"/api/cities/{city}/forecast")
    assert response.status_code == 503 and "isn't configured" in response.json()["detail"]


def test_unknown_city_is_404(user):
    assert user.get("/api/cities/999999/weather").status_code == 404
    assert user.get("/api/cities/999999").json() == {"detail": "City not found."}


# --- forecast -------------------------------------------------------------------------

def test_forecast(user, owm):
    body = user.get(f"/api/cities/{london_id(user)}/forecast").json()
    assert len(body["hourly"]) == 8 and 1 <= len(body["daily"]) <= 5
    assert body["timezone_offset_s"] == 3600 and body["stale"] is False
    assert {"date", "temp_min_c", "temp_max_c", "pop_max", "icon", "theme"} <= set(body["daily"][0])
    user.get(f"/api/cities/{london_id(user)}/forecast")
    assert calls(owm, "/data/2.5/forecast") == 1                # cached


def test_forecast_does_not_touch_history(user, db):
    user.get(f"/api/cities/{london_id(user)}/forecast")
    assert db.query(WeatherSnapshot).count() == 0 and db.query(RecentSearch).count() == 0


def test_httpx_request_logs_are_redacted_even_at_debug_level(user, caplog):
    # httpx logs "HTTP Request: GET <full URL>" itself; the URL contains appid=<key>
    import logging as std_logging

    std_logging.getLogger("httpx").setLevel(std_logging.DEBUG)
    try:
        with caplog.at_level(std_logging.DEBUG):
            user.get(f"/api/cities/{london_id(user)}/weather")
    finally:
        std_logging.getLogger("httpx").setLevel(std_logging.WARNING)
    assert "appid=***" in caplog.text            # the line is still logged, just without the key
    assert FAKE_KEY not in caplog.text


def test_redact_helper():
    from app.core.logging import redact

    assert redact("GET https://x/y?q=a&appid=SECRET&units=metric") == "GET https://x/y?q=a&appid=***&units=metric"
    assert redact("nothing secret here") == "nothing secret here"
