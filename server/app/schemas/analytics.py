"""Response shapes for analytics. Metric; null = no data for that day/value."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.weather import CityOut


class DayOut(BaseModel):
    date: str
    tmin: float | None
    tmax: float | None
    tmean: float | None
    tmean_7d: float | None
    humidity: float | None
    precip: float | None
    wind_max: float | None
    # Only filled when the 1991-2020 normals are available
    normal_tmean: float | None = None
    normal_tmin: float | None = None
    normal_tmax: float | None = None
    normal_p10: float | None = None
    normal_p90: float | None = None
    normal_precip: float | None = None
    anomaly: float | None = None
    category: Literal["warm", "cool", "normal"] | None = None


class DayValue(BaseModel):
    date: str
    value: float


class Extremes(BaseModel):
    hottest: list[DayValue]
    coldest: list[DayValue]
    wettest: list[DayValue]
    windiest: list[DayValue]
    warmest_vs_normal: list[DayValue] = []
    coolest_vs_normal: list[DayValue] = []


class Summary(BaseModel):
    days: int
    days_with_data: int
    coverage: float
    low_coverage: bool
    missing_dates: list[str]
    tmean_avg: float | None
    tmin_avg: float | None
    tmax_avg: float | None
    warmest: DayValue | None
    coldest: DayValue | None
    humidity_avg: float | None
    precip_total: float | None
    precip_days_missing: int
    rainy_days: int
    windiest: DayValue | None
    anomaly_avg: float | None = None
    warm_days: int | None = None
    cool_days: int | None = None


class PeriodOut(BaseModel):
    start: str
    end: str
    days: int


class NormalsInfo(BaseModel):
    available: bool
    baseline: str


class AnalyticsOut(BaseModel):
    city: CityOut
    period: PeriodOut
    normals: NormalsInfo
    daily: list[DayOut]
    summary: Summary
    extremes: Extremes
    stale: bool
    fetched_at: datetime | None


class CompareCity(BaseModel):
    city: CityOut
    normals_available: bool
    series: dict[str, list[float | None]]    # metric -> one value per date in CompareOut.dates
    summary: Summary


class CompareOut(BaseModel):
    days: int
    dates: list[str]
    cities: list[CompareCity]
    stale: bool
