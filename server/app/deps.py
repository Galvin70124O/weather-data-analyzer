"""
Shared FastAPI dependencies.

Scoping rule: anything that belongs to a user is loaded through CurrentUser, and queries
filter on current_user.id. Never take a user id from the URL or the request body.
"""
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.security import decode_session_token
from app.db.session import get_db, get_session_factory
from app.models import User

DbSession = Annotated[Session, Depends(get_db)]
# A session is not thread-safe: work running in parallel threads opens its own from this factory
SessionFactory = Annotated[sessionmaker[Session], Depends(get_session_factory)]

NOT_LOGGED_IN = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You need to log in.")


def get_current_user(request: Request, db: DbSession) -> User:
    token = request.cookies.get(get_settings().cookie_name)
    if not token:
        raise NOT_LOGGED_IN
    decoded = decode_session_token(token)
    if decoded is None:
        raise NOT_LOGGED_IN
    user_id, token_version = decoded
    user = db.get(User, user_id)
    # A deleted user, or a token from before a password change, is not valid any more
    if user is None or user.token_version != token_version:
        raise NOT_LOGGED_IN
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def client_ip(request: Request) -> str:
    # On Render, uvicorn runs with --proxy-headers so request.client is the real visitor
    return request.client.host if request.client else "unknown"
