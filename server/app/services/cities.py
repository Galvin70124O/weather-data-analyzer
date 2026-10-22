"""Cities and the user's own city lists (favourites, recent searches, saved readings)."""
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import City, RecentSearch, User, WeatherSnapshot


def upsert_cities(db: Session, places: list[dict[str, Any]]) -> list[City]:
    """Store geocoding results (once per coordinate) and return them as City rows, in the same order."""
    if not places:
        return []
    db.execute(insert(City).values(places).on_conflict_do_nothing(index_elements=[City.lat, City.lon]))
    db.commit()
    keys = [(p["lat"], p["lon"]) for p in places]
    rows = db.scalars(select(City).where(tuple_(City.lat, City.lon).in_(keys))).all()
    by_coords = {(float(c.lat), float(c.lon)): c for c in rows}
    return [by_coords[key] for key in keys if key in by_coords]


def record_search(db: Session, user: User, city: City) -> None:
    """Remember that the user opened this city (one row per city; the time moves forward)."""
    statement = insert(RecentSearch).values(user_id=user.id, city_id=city.id, searched_at=datetime.now(UTC))
    db.execute(statement.on_conflict_do_update(constraint="uq_recent_searches_user_city",
                                               set_={"searched_at": statement.excluded.searched_at}))
    db.commit()


def save_snapshot(db: Session, user: User, city: City, current: dict[str, Any]) -> None:
    """Keep the reading in the user's history. The same reading (same observed_at) is stored once."""
    values = {
        "user_id": user.id, "city_id": city.id, "observed_at": datetime.fromisoformat(current["observed_at"]),
        "temp_c": current["temp_c"], "feels_like_c": current["feels_like_c"], "humidity": current["humidity"],
        "pressure_hpa": current["pressure_hpa"], "wind_speed_ms": current["wind_speed_ms"],
        "wind_deg": current["wind_deg"], "condition": current["condition"][:40],
        "description": current["description"][:120], "icon": current["icon"][:8],
    }
    db.execute(insert(WeatherSnapshot).values(values)
               .on_conflict_do_nothing(constraint="uq_weather_snapshots_user_city_time"))
    db.commit()
