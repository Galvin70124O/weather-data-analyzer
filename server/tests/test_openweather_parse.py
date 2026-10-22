"""Pure parsing functions: no database, no HTTP."""
from datetime import UTC, datetime

import pytest

from app.services.openweather_parse import parse_current, parse_forecast, parse_geocode, weather_theme
from tests.owm_samples import current_answer, forecast_answer, geocode_answer


@pytest.mark.parametrize("condition_id, icon, theme", [
    (211, "11d", "storm"), (301, "09d", "rain"), (502, "10n", "rain"), (601, "13d", "snow"),
    (741, "50d", "mist"), (800, "01d", "clear-day"), (800, "01n", "clear-night"), (803, "04d", "clouds"),
])
def test_weather_theme(condition_id, icon, theme):
    assert weather_theme(condition_id, icon) == theme


def test_geocode_rounds_coordinates_and_drops_duplicates():
    places = parse_geocode(geocode_answer())
    assert [(p["name"], p["state"], p["country"]) for p in places] == [("London", "England", "GB"), ("London", "Ontario", "CA")]
    assert places[0]["lat"] == 51.5073 and places[0]["lon"] == -0.1276


def test_geocode_skips_places_without_a_country():
    assert parse_geocode([{"name": "Nowhere", "lat": 1, "lon": 2}]) == []


def test_current_weather_fields():
    current = parse_current(current_answer(dt=1_761_134_400))
    assert current["observed_at"] == datetime.fromtimestamp(1_761_134_400, UTC).isoformat()
    assert current["temp_c"] == 14.2 and current["feels_like_c"] == pytest.approx(12.7)
    assert current["wind_deg"] == 230 and current["pressure_hpa"] == 1012 and current["humidity"] == 81
    assert current["theme"] == "rain" and current["is_day"] is True
    assert current["timezone_offset_s"] == 3600
    assert current["sunrise"] == datetime.fromtimestamp(1_761_115_000, UTC).isoformat()
    assert current["sunset"] == datetime.fromtimestamp(1_761_152_000, UTC).isoformat()


def test_forecast_hourly_is_the_next_24_hours():
    forecast = parse_forecast(forecast_answer())
    assert len(forecast["hourly"]) == 8
    times = [datetime.fromisoformat(h["time"]) for h in forecast["hourly"]]
    assert (times[-1] - times[0]).total_seconds() == 21 * 3600     # 8 steps, 3 hours apart


def test_forecast_daily_groups_by_the_city_local_date():
    # Start 22:00 UTC; in a +3h city that is already 01:00 the next day
    start = datetime(2026, 10, 22, 22, tzinfo=UTC)
    utc_days = parse_forecast(forecast_answer(start=start, steps=8, timezone=0))["daily"]
    local_days = parse_forecast(forecast_answer(start=start, steps=8, timezone=3 * 3600))["daily"]
    assert utc_days[0]["date"] == "2026-10-22"
    assert local_days[0]["date"] == "2026-10-23"


def test_forecast_daily_values():
    daily = parse_forecast(forecast_answer())["daily"]
    assert 1 <= len(daily) <= 5
    for day in daily:
        assert day["temp_min_c"] <= day["temp_max_c"]
        assert 0 <= day["pop_max"] <= 1 and day["rain_mm"] >= 0
    full_day = daily[1]                                   # 8 steps of 3 h
    assert full_day["rain_mm"] == pytest.approx(2.4)      # two rainy steps x 1.2 mm
    assert full_day["pop_max"] == 0.6


def test_forecast_daily_icon_comes_from_local_noon():
    daily = parse_forecast(forecast_answer(timezone=0))["daily"]
    assert daily[1]["icon"].endswith("d")                 # the noon step is a daytime icon


def test_geocode_drops_a_second_place_with_the_same_label():
    paris = {"name": "Paris", "state": "Ile-de-France", "country": "FR"}
    places = parse_geocode([{**paris, "lat": 48.8589, "lon": 2.32}, {**paris, "lat": 48.8534, "lon": 2.3488},
                            {"name": "Paris", "state": "Texas", "country": "US", "lat": 33.66, "lon": -95.55}])
    assert [(p["state"], p["lat"]) for p in places] == [("Ile-de-France", 48.8589), ("Texas", 33.66)]
