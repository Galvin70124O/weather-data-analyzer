"""Things a user keeps about cities: favourites, recent searches, saved weather readings."""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.city import City


class FavoriteCity(Base):
    __tablename__ = "favorite_cities"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    city: Mapped[City] = relationship(lazy="joined")

    __table_args__ = (UniqueConstraint("user_id", "city_id", name="uq_favorite_cities_user_city"),)


class RecentSearch(Base):
    """One row per user and city; searched_at moves forward each time the city is opened again."""

    __tablename__ = "recent_searches"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"))
    searched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    city: Mapped[City] = relationship(lazy="joined")

    __table_args__ = (
        UniqueConstraint("user_id", "city_id", name="uq_recent_searches_user_city"),
        Index("ix_recent_searches_user_time", "user_id", "searched_at"),
    )


class WeatherSnapshot(Base):
    """
    A current-weather reading the user looked at (the "History" page of the old app).
    The same reading (same observed_at) is only stored once per user.
    Always metric: Celsius, m/s, hPa.
    """

    __tablename__ = "weather_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))   # when OpenWeatherMap measured it (UTC)
    temp_c: Mapped[float] = mapped_column(Float)
    feels_like_c: Mapped[float] = mapped_column(Float)
    humidity: Mapped[int] = mapped_column(Integer)
    pressure_hpa: Mapped[int] = mapped_column(Integer)
    wind_speed_ms: Mapped[float] = mapped_column(Float)
    wind_deg: Mapped[int | None] = mapped_column(Integer)
    condition: Mapped[str] = mapped_column(String(40))       # e.g. "Rain"
    description: Mapped[str] = mapped_column(String(120))    # e.g. "light rain"
    icon: Mapped[str] = mapped_column(String(8))              # OpenWeatherMap icon code, e.g. "10d"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    city: Mapped[City] = relationship(lazy="joined")

    __table_args__ = (
        UniqueConstraint("user_id", "city_id", "observed_at", name="uq_weather_snapshots_user_city_time"),
        Index("ix_weather_snapshots_user_time", "user_id", "observed_at"),
    )
