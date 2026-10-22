"""Historical daily weather (Open-Meteo archive) and 1991-2020 climate normals, per city."""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, SmallInteger, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DailyWeather(Base):
    """
    One day of observed weather for a city, in the city's local calendar. Metric.
    is_final: the day is old enough (more than 7 days ago) that Open-Meteo won't revise it,
    so it is never fetched again. Newer days are refetched at most every few hours.
    A NULL value = Open-Meteo had no data for it (kept as NULL, never replaced by 0).
    """

    __tablename__ = "daily_weather"

    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    tmin: Mapped[float | None] = mapped_column(Float)
    tmax: Mapped[float | None] = mapped_column(Float)
    tmean: Mapped[float | None] = mapped_column(Float)
    humidity: Mapped[float | None] = mapped_column(Float)
    precip: Mapped[float | None] = mapped_column(Float)
    wind_max: Mapped[float | None] = mapped_column(Float)
    is_final: Mapped[bool] = mapped_column(Boolean, default=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ClimateNormal(Base):
    """The 1991-2020 normal for one day of the year (1-365). Computed once per city, never refetched."""

    __tablename__ = "climate_normals"

    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"), primary_key=True)
    day_of_year: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    normal_tmean: Mapped[float | None] = mapped_column(Float)
    normal_tmin: Mapped[float | None] = mapped_column(Float)
    normal_tmax: Mapped[float | None] = mapped_column(Float)
    normal_p10: Mapped[float | None] = mapped_column(Float)
    normal_p90: Mapped[float | None] = mapped_column(Float)
    normal_precip: Mapped[float | None] = mapped_column(Float)
    normal_humidity: Mapped[float | None] = mapped_column(Float)
    normal_wind_max: Mapped[float | None] = mapped_column(Float)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
