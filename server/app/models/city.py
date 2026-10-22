from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class City(Base):
    """
    A place from OpenWeatherMap geocoding. Shared by all users (it isn't personal data).

    Rows are only created from geocoding results, never from what a browser sends,
    so names and coordinates can be trusted.
    """

    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(120))
    country: Mapped[str] = mapped_column(String(2))           # ISO 3166 code, e.g. "GB"
    # 4 decimals = about 11 m: plenty for weather, and the same place always gets the same row
    lat: Mapped[Decimal] = mapped_column(Numeric(7, 4))
    lon: Mapped[Decimal] = mapped_column(Numeric(7, 4))
    # The city's offset from UTC (seconds), learned from the first weather answer. Used to know
    # which day is "yesterday" there. NULL until known.
    utc_offset_s: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("lat", "lon", name="uq_cities_lat_lon"),)

    @property
    def label(self) -> str:
        """"London, GB" or "London, Ontario, CA". A state named like the city is left out: "Cairo, EG"."""
        state = self.state if self.state and self.state.casefold() != self.name.casefold() else None
        return ", ".join(part for part in [self.name, state, self.country] if part)
