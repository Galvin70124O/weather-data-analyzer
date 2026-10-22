"""City search (autocomplete), current weather and forecast for a city."""
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.deps import CurrentUser, DbSession
from app.models import City
from app.schemas.weather import CityOut, CurrentWeatherOut, ForecastOut
from app.services import cities as city_service
from app.services import openweather
from app.services.openweather_parse import parse_current, parse_forecast, parse_geocode

router = APIRouter(prefix="/api/cities", tags=["cities"])


def get_city_or_404(db: DbSession, city_id: int) -> City:
    city = db.get(City, city_id)
    if city is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "City not found.")
    return city


@router.get("/search", response_model=list[CityOut])
def search_cities(db: DbSession, user: CurrentUser,
                  q: Annotated[str, Query(min_length=2, max_length=100, description="Part of a city name")]) -> list[City]:
    """Autocomplete: up to 5 places, e.g. "London, GB" and "London, Ontario, CA". No match = empty list."""
    if not openweather.normalize_query(q):
        return []
    result = openweather.geocode(db, q)
    return city_service.upsert_cities(db, parse_geocode(result.data))


@router.get("/{city_id}", response_model=CityOut)
def read_city(city_id: int, db: DbSession, user: CurrentUser) -> City:
    return get_city_or_404(db, city_id)


@router.get("/{city_id}/weather", response_model=CurrentWeatherOut)
def city_weather(city_id: int, db: DbSession, user: CurrentUser) -> dict:
    """Current weather. Opening a city also adds it to your recent searches and your history."""
    city = get_city_or_404(db, city_id)
    result = openweather.current_weather(db, float(city.lat), float(city.lon))
    current = parse_current(result.data)
    city_service.record_search(db, user, city)
    city_service.save_snapshot(db, user, city, current)
    return {"city": city, "weather": current, "fetched_at": result.fetched_at, "stale": result.stale}


@router.get("/{city_id}/forecast", response_model=ForecastOut)
def city_forecast(city_id: int, db: DbSession, user: CurrentUser) -> dict:
    """Next 24 hours (3-hour steps) and 5 days, in the city's local time."""
    city = get_city_or_404(db, city_id)
    result = openweather.forecast(db, float(city.lat), float(city.lon))
    return {"city": city, **parse_forecast(result.data), "fetched_at": result.fetched_at, "stale": result.stale}
