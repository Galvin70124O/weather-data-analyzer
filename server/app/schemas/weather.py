"""Response shapes for cities, weather, favourites and history. Always metric."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Theme = Literal["clear-day", "clear-night", "clouds", "rain", "storm", "snow", "mist"]


class CityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    state: str | None
    country: str
    lat: float
    lon: float
    label: str            # "London, GB"


class Condition(BaseModel):
    condition: str        # "Rain"
    condition_id: int     # OpenWeatherMap code, e.g. 500
    description: str      # "light rain"
    icon: str             # "10d"
    theme: Theme          # for the UI's background/accent


class CurrentWeather(Condition):
    observed_at: datetime
    timezone_offset_s: int     # the city's offset from UTC, for its local time
    temp_c: float
    feels_like_c: float
    temp_min_c: float | None
    temp_max_c: float | None
    humidity: int
    pressure_hpa: int
    wind_speed_ms: float
    wind_deg: int | None
    wind_gust_ms: float | None
    clouds_pct: int | None
    visibility_m: int | None
    sunrise: datetime | None
    sunset: datetime | None
    is_day: bool


class CurrentWeatherOut(BaseModel):
    city: CityOut
    weather: CurrentWeather
    fetched_at: datetime
    stale: bool = Field(description="True: the weather service failed and this is an older cached answer")


class HourlyStep(Condition):
    time: datetime
    temp_c: float
    feels_like_c: float
    pop: float                 # chance of rain, 0..1
    rain_mm: float
    wind_speed_ms: float
    wind_deg: int | None


class DailyForecast(Condition):
    date: str                  # local date in the city, YYYY-MM-DD
    temp_min_c: float
    temp_max_c: float
    pop_max: float
    rain_mm: float
    humidity_mean: int
    wind_max_ms: float


class ForecastOut(BaseModel):
    city: CityOut
    timezone_offset_s: int
    hourly: list[HourlyStep]
    daily: list[DailyForecast]
    fetched_at: datetime
    stale: bool


class FavoriteIn(BaseModel):
    city_id: int


class FavoriteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    city: CityOut
    created_at: datetime


class RecentSearchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    city: CityOut
    searched_at: datetime


class SnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    city: CityOut
    observed_at: datetime
    temp_c: float
    feels_like_c: float
    humidity: int
    pressure_hpa: int
    wind_speed_ms: float
    wind_deg: int | None
    condition: str
    description: str
    icon: str


class DashboardCard(BaseModel):
    city: CityOut
    weather: CurrentWeather | None     # None if the weather service failed and nothing is cached
    stale: bool
    error: str | None


class DashboardOut(BaseModel):
    username: str
    favorites: list[DashboardCard]
    recent: list[RecentSearchOut]
