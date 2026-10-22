"""
OpenWeatherMap: geocoding, current weather, 5-day forecast. Every call goes through the cache.

The API key is only added here, right before the request. httpx error messages contain the
full URL (key included), so they are NEVER logged or shown: only the endpoint and a reason.
"""
import logging
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.cache import CachedResult, cached_fetch
from app.services.errors import UpstreamError, UpstreamNotConfigured, UpstreamNotFound
from app.services.http import get_http_client

log = logging.getLogger(__name__)

GEOCODE_LIMIT = 5


def _get(path: str, params: dict[str, Any]) -> Any:
    settings = get_settings()
    if settings.openweather_api_key is None:
        log.error("OPENWEATHER_API_KEY is not set")
        raise UpstreamNotConfigured()
    query = {**params, "appid": settings.openweather_api_key.get_secret_value()}
    try:
        response = get_http_client().get(settings.openweather_base_url + path, params=query)
    except httpx.TimeoutException:
        log.warning("OpenWeatherMap %s: timeout", path)
        raise UpstreamError() from None      # "from None": don't chain the httpx error (it holds the URL)
    except httpx.HTTPError as error:
        log.warning("OpenWeatherMap %s: network error (%s)", path, type(error).__name__)
        raise UpstreamError() from None

    if response.status_code in (401, 403):
        log.error("OpenWeatherMap %s: the API key was rejected (HTTP %s)", path, response.status_code)
        raise UpstreamError()                # users just see "unavailable", not "bad key"
    if response.status_code == 404:
        raise UpstreamNotFound()
    if response.status_code == 429:
        log.warning("OpenWeatherMap %s: rate limited", path)
        raise UpstreamError()
    if response.status_code >= 400:
        log.warning("OpenWeatherMap %s: HTTP %s", path, response.status_code)
        raise UpstreamError()
    try:
        return response.json()
    except ValueError:
        log.warning("OpenWeatherMap %s: answer was not JSON", path)
        raise UpstreamError() from None


def normalize_query(query: str) -> str:
    """ "  New   York " -> "new york" (so different spellings share one cache entry)."""
    return " ".join(query.lower().split())


def geocode(db: Session, query: str) -> CachedResult:
    q = normalize_query(query)
    return cached_fetch(db, f"owm:geocode:{q}:{GEOCODE_LIMIT}", get_settings().cache_ttl_geocode,
                        lambda: _get("/geo/1.0/direct", {"q": q, "limit": GEOCODE_LIMIT}))


def _coords(lat: float, lon: float) -> str:
    return f"{float(lat):.4f},{float(lon):.4f}"


def current_weather(db: Session, lat: float, lon: float) -> CachedResult:
    return cached_fetch(db, f"owm:current:{_coords(lat, lon)}", get_settings().cache_ttl_current,
                        lambda: _get("/data/2.5/weather", {"lat": lat, "lon": lon, "units": "metric"}))


def forecast(db: Session, lat: float, lon: float) -> CachedResult:
    return cached_fetch(db, f"owm:forecast:{_coords(lat, lon)}", get_settings().cache_ttl_forecast,
                        lambda: _get("/data/2.5/forecast", {"lat": lat, "lon": lon, "units": "metric"}))
