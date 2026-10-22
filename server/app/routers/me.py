"""The logged-in user's own account."""
from fastapi import APIRouter

from app.deps import CurrentUser, DbSession
from app.models import User
from app.schemas.auth import PreferencesIn, UserOut

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("", response_model=UserOut)
def read_me(user: CurrentUser) -> User:
    return user


@router.patch("", response_model=UserOut)
def update_preferences(body: PreferencesIn, user: CurrentUser, db: DbSession) -> User:
    user.units = body.units
    db.commit()
    return user
