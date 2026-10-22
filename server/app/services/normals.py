"""
1991-2020 climate normals per city: fetched lazily the first time a city's analytics are
opened, computed (app/analytics/normals.py), stored in climate_normals, and NEVER refetched.
"""
import logging
from datetime import date

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.analytics.daily import daily_frame
from app.analytics.normals import DAYS, NORMAL_COLUMNS, compute_normals
from app.models import City, ClimateNormal
from app.services.errors import UpstreamError
from app.services.openmeteo import fetch_archive

log = logging.getLogger(__name__)

BASELINE = "1991-2020"
BASELINE_START, BASELINE_END = date(1991, 1, 1), date(2020, 12, 31)


def load_normals(db: Session, city: City) -> pd.DataFrame | None:
    rows = db.scalars(select(ClimateNormal).where(ClimateNormal.city_id == city.id)).all()
    if len(rows) < DAYS:
        return None
    return pd.DataFrame([{"day_of_year": r.day_of_year, **{c: getattr(r, c) for c in NORMAL_COLUMNS}} for r in rows]) \
        .set_index("day_of_year").astype(float).sort_index()


def ensure_normals(db: Session, city: City) -> pd.DataFrame | None:
    """
    The city's normals, fetching and storing them the first time.
    Returns None if they aren't stored yet and Open-Meteo fails: the analytics still work
    without them, and the next visit tries again.
    """
    normals = load_normals(db, city)
    if normals is not None:
        return normals
    try:
        rows, _ = fetch_archive(float(city.lat), float(city.lon), BASELINE_START, BASELINE_END)
    except UpstreamError:
        log.warning("Climate normals for city %s: Open-Meteo failed, will retry next time", city.id)
        return None
    normals = compute_normals(daily_frame(rows, BASELINE_START, BASELINE_END))
    values = [{"city_id": city.id, "day_of_year": int(day),
               **{c: (None if pd.isna(row[c]) else float(row[c])) for c in NORMAL_COLUMNS}}
              for day, row in normals.iterrows()]
    db.execute(insert(ClimateNormal).values(values).on_conflict_do_nothing(
        index_elements=[ClimateNormal.city_id, ClimateNormal.day_of_year]))
    db.commit()
    return load_normals(db, city)


def has_normals(db: Session, city: City) -> bool:
    return (db.scalar(select(func.count()).select_from(ClimateNormal).where(ClimateNormal.city_id == city.id)) or 0) >= DAYS
