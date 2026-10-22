"""History analytics for one city, and side-by-side comparison of 2-3 cities."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.deps import CurrentUser, DbSession
from app.models import City
from app.routers.cities import get_city_or_404
from app.schemas.analytics import AnalyticsOut, CompareOut
from app.services import analytics

router = APIRouter(prefix="/api", tags=["analytics"])


def period_days(days: Annotated[int, Query(description="30, 90 or 365")] = 30) -> int:
    # (A Literal[30, 90, 365] type would reject "30": query values arrive as text)
    if days not in analytics.PERIODS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "days must be 30, 90 or 365.")
    return days


Days = Annotated[int, Depends(period_days)]


@router.get("/cities/{city_id}/analytics", response_model=AnalyticsOut)
def city_analytics(city_id: int, db: DbSession, user: CurrentUser, days: Days) -> dict:
    """
    The last 30, 90 or 365 complete days: daily min/max/mean, 7-day rolling mean, humidity,
    rain, wind, comparison with the 1991-2020 normals, a summary and the extreme days.
    The first time a city is opened, its normals are fetched (a few seconds) and stored for good.
    """
    return analytics.city_analytics(db, get_city_or_404(db, city_id), days)


@router.get("/analytics/compare", response_model=CompareOut)
def compare(db: DbSession, user: CurrentUser,
            city_id: Annotated[list[int], Query(description="2 or 3 city ids, e.g. ?city_id=1&city_id=2")],
            days: Days) -> dict:
    ids = list(dict.fromkeys(city_id))          # drop repeats, keep the order
    if not 2 <= len(ids) <= 3:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Compare 2 or 3 different cities.")
    cities: list[City] = [get_city_or_404(db, i) for i in ids]
    return analytics.compare(db, cities, days)
