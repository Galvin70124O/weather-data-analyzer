"""
Pure functions that turn OpenWeatherMap JSON into the shapes our API returns.
No database, no HTTP: easy to unit test. Everything is metric (Celsius, m/s, hPa, mm).
"""
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

DAILY_DAYS = 5
HOURLY_ENTRIES = 8          # 8 x 3 hours = the next 24 hours


def round_coordinate(value: float) -> float:
    return round(float(value), 4)


def utc_from_unix(seconds: int) -> datetime:
    return datetime.fromtimestamp(int(seconds), tz=UTC)


def weather_theme(condition_id: int, icon: str) -> str:
    """
    One of: clear-day, clear-night, clouds, rain, storm, snow, mist.
    The UI uses it for the background gradient and accent colour.
    OpenWeatherMap condition codes: 2xx storm, 3xx drizzle, 5xx rain, 6xx snow, 7xx haze/fog, 800 clear, 80x clouds.
    """
    group = condition_id // 100
    if group == 2:
        return "storm"
    if group in (3, 5):
        return "rain"
    if group == 6:
        return "snow"
    if group == 7:
        return "mist"
    if condition_id == 800:
        return "clear-night" if icon.endswith("n") else "clear-day"
    return "clouds"


def parse_geocode(payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Geocoding results: name, state, country, lat, lon.
    Duplicates are dropped: the same coordinates, or the same label (OpenWeatherMap returns
    e.g. two "Paris, Ile-de-France, FR" a few hundred metres apart; the first, best match wins).
    """
    places, seen = [], set()
    for item in payload:
        if not item.get("country"):
            continue
        lat, lon = round_coordinate(item["lat"]), round_coordinate(item["lon"])
        label = (item["name"].lower(), (item.get("state") or "").lower(), item["country"].upper())
        if (lat, lon) in seen or label in seen:
            continue
        seen.update({(lat, lon), label})
        places.append({"name": item["name"], "state": item.get("state"), "country": item["country"], "lat": lat, "lon": lon})
    return places


def _condition(entry: dict[str, Any]) -> dict[str, Any]:
    weather = entry["weather"][0]
    return {"condition": weather["main"], "condition_id": weather["id"], "description": weather["description"],
            "icon": weather["icon"], "theme": weather_theme(weather["id"], weather["icon"])}


def parse_current(payload: dict[str, Any]) -> dict[str, Any]:
    main, wind, sys = payload["main"], payload.get("wind", {}), payload.get("sys", {})
    return {
        "observed_at": utc_from_unix(payload["dt"]).isoformat(),
        "timezone_offset_s": int(payload.get("timezone", 0)),
        "temp_c": main["temp"],
        "feels_like_c": main["feels_like"],
        "temp_min_c": main.get("temp_min"),
        "temp_max_c": main.get("temp_max"),
        "humidity": main["humidity"],
        "pressure_hpa": main["pressure"],
        "wind_speed_ms": wind.get("speed", 0.0),
        "wind_deg": wind.get("deg"),
        "wind_gust_ms": wind.get("gust"),
        "clouds_pct": payload.get("clouds", {}).get("all"),
        "visibility_m": payload.get("visibility"),
        "sunrise": utc_from_unix(sys["sunrise"]).isoformat() if sys.get("sunrise") else None,
        "sunset": utc_from_unix(sys["sunset"]).isoformat() if sys.get("sunset") else None,
        "is_day": payload["weather"][0]["icon"].endswith("d"),
        **_condition(payload),
    }


def _local_date(unix_seconds: int, offset_s: int) -> date:
    return (utc_from_unix(unix_seconds) + timedelta(seconds=offset_s)).date()


def _rain_mm(entry: dict[str, Any]) -> float:
    return float(entry.get("rain", {}).get("3h", 0.0)) + float(entry.get("snow", {}).get("3h", 0.0))


def parse_forecast(payload: dict[str, Any]) -> dict[str, Any]:
    """
    The 5-day / 3-hour forecast as:
      hourly: the next 24 hours (8 steps of 3 hours)
      daily:  up to 5 days in the city's local time, with min/max temperature, rain, wind, and the
              condition of the step closest to local noon
    """
    offset = int(payload.get("city", {}).get("timezone", 0))
    entries = payload["list"]

    hourly = [{
        "time": utc_from_unix(e["dt"]).isoformat(),
        "temp_c": e["main"]["temp"],
        "feels_like_c": e["main"]["feels_like"],
        "pop": round(float(e.get("pop", 0.0)), 2),          # probability of rain, 0..1
        "rain_mm": round(_rain_mm(e), 2),
        "wind_speed_ms": e.get("wind", {}).get("speed", 0.0),
        "wind_deg": e.get("wind", {}).get("deg"),
        **_condition(e),
    } for e in entries[:HOURLY_ENTRIES]]

    by_day: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for e in entries:
        by_day[_local_date(e["dt"], offset)].append(e)

    daily = []
    for day in sorted(by_day)[:DAILY_DAYS]:
        steps = by_day[day]
        noon = min(steps, key=lambda e: abs((utc_from_unix(e["dt"]) + timedelta(seconds=offset)).hour - 12))
        daily.append({
            "date": day.isoformat(),
            "temp_min_c": min(e["main"]["temp_min"] for e in steps),
            "temp_max_c": max(e["main"]["temp_max"] for e in steps),
            "pop_max": round(max(float(e.get("pop", 0.0)) for e in steps), 2),
            "rain_mm": round(sum(_rain_mm(e) for e in steps), 1),
            "humidity_mean": round(sum(e["main"]["humidity"] for e in steps) / len(steps)),
            "wind_max_ms": max(e.get("wind", {}).get("speed", 0.0) for e in steps),
            **_condition(noon),
        })
    return {"timezone_offset_s": offset, "hourly": hourly, "daily": daily}
