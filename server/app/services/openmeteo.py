"""
Open-Meteo historical weather (archive API), stored per city and day in daily_weather.

Open-Meteo's free tier is for non-commercial use, with daily call limits, so we ask for as
little as possible:
- a stored day older than FINAL_AFTER_DAYS is final and never fetched again;
- newer days can still be revised by Open-Meteo, so they are refetched, but at most every
  RECENT_TTL;
- one request covers exactly the span of days that are missing or due for a refresh.
Dates are in the city's local calendar (timezone=auto). Today isn't over yet, so the last
complete day is the city's local yesterday.
"""
import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import City, DailyWeather
from app.services.errors import UpstreamError
from app.services.http import get_http_client

log = logging.getLogger(__name__)

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FINAL_AFTER_DAYS = 7
RECENT_TTL = timedelta(hours=6)

# Open-Meteo variable -> our column
DAILY_VARIABLES = {
    "temperature_2m_min": "tmin",
    "temperature_2m_max": "tmax",
    "temperature_2m_mean": "tmean",
    "relative_humidity_2m_mean": "humidity",
    "precipitation_sum": "precip",
    "wind_speed_10m_max": "wind_max",
}
METRIC_COLUMNS = list(DAILY_VARIABLES.values())


@dataclass(frozen=True)
class DailyResult:
    records: list[dict[str, Any]]    # {"date": date, "tmin": ..., ...} for the days we have
    stale: bool                       # True: Open-Meteo failed, some days may be missing or out of date
    fetched_at: datetime | None       # oldest fetch time among the returned days


def fetch_archive(lat: float, lon: float, start: date, end: date) -> tuple[list[dict[str, Any]], int]:
    """One archive request. Returns (rows with local dates, the place's UTC offset in seconds)."""
    params = {"latitude": lat, "longitude": lon, "start_date": start.isoformat(), "end_date": end.isoformat(),
              "daily": ",".join(DAILY_VARIABLES), "timezone": "auto", "wind_speed_unit": "ms"}
    try:
        response = get_http_client().get(ARCHIVE_URL, params=params, timeout=30.0)
    except httpx.TimeoutException:
        log.warning("Open-Meteo archive: timeout")
        raise UpstreamError() from None
    except httpx.HTTPError as error:
        log.warning("Open-Meteo archive: network error (%s)", type(error).__name__)
        raise UpstreamError() from None
    if response.status_code >= 400:
        log.warning("Open-Meteo archive: HTTP %s", response.status_code)   # 429 = daily limit reached
        raise UpstreamError()
    try:
        body = response.json()
        daily = body["daily"]
        rows = [{"date": date.fromisoformat(day),
                 **{column: daily.get(variable, [None] * len(daily["time"]))[i] for variable, column in DAILY_VARIABLES.items()}}
                for i, day in enumerate(daily["time"])]
        return rows, int(body.get("utc_offset_seconds", 0))
    except (ValueError, KeyError, TypeError, IndexError):
        log.warning("Open-Meteo archive: unexpected answer")
        raise UpstreamError() from None


def local_yesterday(city: City, now: datetime) -> date:
    """The last complete day in the city's own calendar."""
    offset = timedelta(seconds=city.utc_offset_s or 0)
    return (now + offset).date() - timedelta(days=1)


def _needs_fetch(row: DailyWeather | None, now: datetime) -> bool:
    return row is None or (not row.is_final and row.fetched_at < now - RECENT_TTL)


def ensure_daily(db: Session, city: City, start: date, end: date, now: datetime | None = None) -> DailyResult:
    """Daily weather for start..end (inclusive), fetching from Open-Meteo only what is needed."""
    now = now or datetime.now(UTC)
    stored = {row.date: row for row in db.scalars(
        select(DailyWeather).where(DailyWeather.city_id == city.id, DailyWeather.date.between(start, end)))}
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    needed = [d for d in days if _needs_fetch(stored.get(d), now)]

    stale = False
    if needed:
        try:
            rows, offset = fetch_archive(float(city.lat), float(city.lon), min(needed), max(needed))
            _save(db, city, rows, offset, now)
            stored = {row.date: row for row in db.scalars(
                select(DailyWeather).where(DailyWeather.city_id == city.id, DailyWeather.date.between(start, end)))}
        except UpstreamError:
            if not stored:
                raise
            stale = True      # show what we have; the missing days stay explicit gaps

    records = [{"date": row.date, **{c: getattr(row, c) for c in METRIC_COLUMNS}} for row in stored.values()]
    fetched = min((row.fetched_at for row in stored.values()), default=None)
    return DailyResult(sorted(records, key=lambda r: r["date"]), stale, fetched)


def _save(db: Session, city: City, rows: list[dict[str, Any]], offset_s: int, now: datetime) -> None:
    if city.utc_offset_s != offset_s:
        city.utc_offset_s = offset_s
    final_before = (now + timedelta(seconds=offset_s)).date() - timedelta(days=FINAL_AFTER_DAYS)
    today_local = (now + timedelta(seconds=offset_s)).date()
    values = [{"city_id": city.id, **row, "is_final": row["date"] < final_before, "fetched_at": now}
              for row in rows if row["date"] < today_local]          # never store the unfinished day
    if values:
        statement = insert(DailyWeather).values(values)
        db.execute(statement.on_conflict_do_update(
            index_elements=[DailyWeather.city_id, DailyWeather.date],
            set_={c: statement.excluded[c] for c in [*METRIC_COLUMNS, "is_final", "fetched_at"]}))
    db.commit()
