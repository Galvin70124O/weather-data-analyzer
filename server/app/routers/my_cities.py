"""The logged-in user's favourites, recent searches, saved history and dashboard. All scoped to the user."""
import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.deps import CurrentUser, DbSession, SessionFactory
from app.models import City, FavoriteCity, RecentSearch, WeatherSnapshot
from app.schemas.weather import DashboardOut, FavoriteIn, FavoriteOut, RecentSearchOut, SnapshotOut
from app.services import openweather
from app.services.errors import UpstreamError
from app.services.openweather_parse import parse_current

router = APIRouter(prefix="/api", tags=["my cities"])
log = logging.getLogger(__name__)

MAX_FAVORITES = 20


# --- favourites ----------------------------------------------------------------------

@router.get("/favorites", response_model=list[FavoriteOut])
def list_favorites(db: DbSession, user: CurrentUser) -> list[FavoriteCity]:
    return list(db.scalars(select(FavoriteCity).where(FavoriteCity.user_id == user.id)
                           .order_by(FavoriteCity.created_at, FavoriteCity.id)))


@router.post("/favorites", response_model=FavoriteOut, status_code=status.HTTP_201_CREATED)
def add_favorite(body: FavoriteIn, response: Response, db: DbSession, user: CurrentUser) -> FavoriteCity:
    if db.get(City, body.city_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "City not found.")
    existing = db.scalar(select(FavoriteCity).where(FavoriteCity.user_id == user.id, FavoriteCity.city_id == body.city_id))
    if existing is not None:
        response.status_code = status.HTTP_200_OK          # already a favourite: nothing to do
        return existing
    count = len(list_favorites(db, user))
    if count >= MAX_FAVORITES:
        raise HTTPException(status.HTTP_409_CONFLICT, f"You can have up to {MAX_FAVORITES} favourite cities.")
    favorite = FavoriteCity(user_id=user.id, city_id=body.city_id)
    db.add(favorite)
    try:
        db.commit()
    except IntegrityError:                                  # added twice at the same moment
        db.rollback()
        response.status_code = status.HTTP_200_OK
        favorite = db.scalar(select(FavoriteCity).where(FavoriteCity.user_id == user.id, FavoriteCity.city_id == body.city_id))
    db.refresh(favorite)
    return favorite


@router.delete("/favorites/{city_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(city_id: int, db: DbSession, user: CurrentUser) -> None:
    removed = db.execute(delete(FavoriteCity).where(FavoriteCity.user_id == user.id, FavoriteCity.city_id == city_id))
    db.commit()
    if removed.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That city isn't one of your favourites.")


# --- recent searches -----------------------------------------------------------------

@router.get("/searches/recent", response_model=list[RecentSearchOut])
def recent_searches(db: DbSession, user: CurrentUser,
                    limit: Annotated[int, Query(ge=1, le=20)] = 8) -> list[RecentSearch]:
    return list(db.scalars(select(RecentSearch).where(RecentSearch.user_id == user.id)
                           .order_by(RecentSearch.searched_at.desc()).limit(limit)))


@router.delete("/searches/recent", status_code=status.HTTP_204_NO_CONTENT)
def clear_recent_searches(db: DbSession, user: CurrentUser) -> None:
    db.execute(delete(RecentSearch).where(RecentSearch.user_id == user.id))
    db.commit()


# --- history (saved readings) --------------------------------------------------------

@router.get("/history", response_model=list[SnapshotOut])
def history(db: DbSession, user: CurrentUser, city_id: int | None = None,
            limit: Annotated[int, Query(ge=1, le=500)] = 100) -> list[WeatherSnapshot]:
    query = select(WeatherSnapshot).where(WeatherSnapshot.user_id == user.id)
    if city_id is not None:
        query = query.where(WeatherSnapshot.city_id == city_id)
    return list(db.scalars(query.order_by(WeatherSnapshot.observed_at.desc()).limit(limit)))


# --- dashboard -----------------------------------------------------------------------

DASHBOARD_MAX_PARALLEL = 5      # at most this many weather lookups at the same time


def load_card(session_factory: sessionmaker[Session], city: City) -> dict:
    """One favourite's card. Runs in a worker thread, with its own database session.
    Never raises: a failing city gets an error message on its own card only."""
    try:
        with session_factory() as db:
            result = openweather.current_weather(db, float(city.lat), float(city.lon))
        return {"city": city, "weather": parse_current(result.data), "stale": result.stale, "error": None}
    except UpstreamError as error:
        return {"city": city, "weather": None, "stale": False, "error": error.public_message}
    except Exception:            # e.g. an unexpected answer shape: log it, but keep the other cards
        log.exception("Dashboard card for city %s failed", city.id)
        return {"city": city, "weather": None, "stale": False, "error": UpstreamError.public_message}


@router.get("/dashboard", response_model=DashboardOut)
async def dashboard(db: DbSession, user: CurrentUser, session_factory: SessionFactory) -> dict:
    """Greeting, favourite cities with their current weather (cached), and recent searches.
    The favourites' weather is fetched in parallel (max DASHBOARD_MAX_PARALLEL at once).
    Unlike opening a city, this doesn't add anything to recent searches or history."""
    favorites = await asyncio.to_thread(list_favorites, db, user)
    recent = await asyncio.to_thread(recent_searches, db, user, 8)
    limit = asyncio.Semaphore(DASHBOARD_MAX_PARALLEL)

    async def card(city: City) -> dict:
        async with limit:
            return await asyncio.to_thread(load_card, session_factory, city)

    cards = await asyncio.gather(*(card(favorite.city) for favorite in favorites))
    return {"username": user.username, "favorites": list(cards), "recent": recent}
