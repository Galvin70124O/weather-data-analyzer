"""
Glue between storage and the pure analytics functions: load the days and normals, run
app/analytics/*, shape the answer. No calculations of its own.
"""
from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.analytics.compare import compare_cities
from app.analytics.daily import daily_frame, extremes, rolling_mean, summarize, to_records
from app.analytics.normals import attach_normals
from app.models import City
from app.services import normals as normals_service
from app.services.openmeteo import ensure_daily, local_yesterday

ROLLING_DAYS = 7
PERIODS = (30, 90, 365)


def period_frame(db: Session, city: City, days: int, now: datetime | None = None) -> tuple[pd.DataFrame, bool, Any, bool]:
    """
    The last `days` complete days for a city, with the 7-day rolling mean and (if available)
    the normals attached. The rolling mean also uses the 6 days before the period, so it isn't
    empty at the start of the chart.
    Returns (frame, stale, fetched_at, normals_available).
    """
    now = now or datetime.now(UTC)
    end = local_yesterday(city, now)
    start = end - timedelta(days=days - 1)
    warm_up = start - timedelta(days=ROLLING_DAYS - 1)

    result = ensure_daily(db, city, warm_up, end, now)
    end = local_yesterday(city, now)        # the first fetch may have taught us the city's UTC offset
    frame = daily_frame(result.records, warm_up, end)
    frame["tmean_7d"] = rolling_mean(frame["tmean"], window=ROLLING_DAYS, min_periods=5)

    normals = normals_service.ensure_normals(db, city)
    if normals is not None:
        frame = attach_normals(frame, normals)
    period = frame.loc[pd.Timestamp(end - timedelta(days=days - 1)):pd.Timestamp(end)]
    return period, result.stale, result.fetched_at, normals is not None


def city_analytics(db: Session, city: City, days: int) -> dict[str, Any]:
    frame, stale, fetched_at, normals_available = period_frame(db, city, days)
    return {
        "city": city,
        "period": {"start": frame.index[0].date().isoformat(), "end": frame.index[-1].date().isoformat(), "days": days},
        "normals": {"available": normals_available, "baseline": normals_service.BASELINE},
        "daily": to_records(frame),
        "summary": summarize(frame),
        "extremes": extremes(frame),
        "stale": stale,
        "fetched_at": fetched_at,
    }


def compare(db: Session, cities: list[City], days: int) -> dict[str, Any]:
    frames, stale = {}, False
    normals_available = {}
    for city in cities:
        frame, city_stale, _, has_normals = period_frame(db, city, days)
        frames[city.id] = frame
        stale = stale or city_stale
        normals_available[city.id] = has_normals
    result = compare_cities(frames)
    return {
        "days": days,
        "dates": result["dates"],
        "cities": [{"city": city, "normals_available": normals_available[city.id], **result["cities"][city.id]}
                   for city in cities],
        "stale": stale,
    }
