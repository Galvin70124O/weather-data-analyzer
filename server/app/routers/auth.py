"""Register, log in, log out, change password. The session lives in an httpOnly cookie."""
from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.security import create_session_token, hash_password, verify_dummy_password, verify_password
from app.deps import CurrentUser, DbSession, client_ip
from app.models import User
from app.schemas.auth import ChangePasswordIn, LoginIn, RegisterIn, UserOut
from app.services import rate_limit

router = APIRouter(prefix="/api/auth", tags=["auth"])

INVALID_LOGIN = "Invalid username/email or password."


def set_session_cookie(response: Response, user: User) -> None:
    settings = get_settings()
    response.set_cookie(
        settings.cookie_name,
        create_session_token(user.id, user.token_version),
        max_age=settings.jwt_expire_days * 24 * 3600,
        httponly=True,                 # page scripts can't read it
        secure=settings.cookie_secure,  # HTTPS only in production
        samesite="lax",                # not sent on cross-site POSTs (CSRF protection)
        path="/",
    )


def find_user_by_login(db: DbSession, identifier: str) -> User | None:
    # Usernames can't contain "@", so an identifier with "@" is always an email
    column = User.email if "@" in identifier else User.username
    return db.scalar(select(User).where(func.lower(column) == identifier.lower()))


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, response: Response, db: DbSession) -> User:
    taken = db.scalar(select(User.id).where(or_(func.lower(User.username) == body.username.lower(),
                                                func.lower(User.email) == body.email)))
    if taken is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "That username or email is already taken.")
    user = User(username=body.username, email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:   # two sign-ups with the same name at the same moment
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "That username or email is already taken.")
    db.refresh(user)
    set_session_cookie(response, user)
    return user


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, request: Request, response: Response, db: DbSession) -> User:
    identifier = body.identifier.strip().lower()
    ip = client_ip(request)
    wait = rate_limit.seconds_until_allowed(db, identifier, ip)
    if wait:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            f"Too many failed logins. Try again in {max(1, round(wait / 60))} minute(s).",
                            headers={"Retry-After": str(wait)})

    user = find_user_by_login(db, identifier)
    if user is None:
        verify_dummy_password(body.password)   # same timing as a wrong password
        ok = False
    else:
        ok = verify_password(body.password, user.password_hash)
    rate_limit.record_attempt(db, identifier, ip, succeeded=ok)
    if not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_LOGIN)
    set_session_cookie(response, user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(settings.cookie_name, path="/", secure=settings.cookie_secure, httponly=True, samesite="lax")


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(body: ChangePasswordIn, request: Request, response: Response, user: CurrentUser, db: DbSession) -> None:
    # Same rate limit as login, so a stolen session can't be used to guess the password
    identifier = f"password-change:{user.id}"
    ip = client_ip(request)
    wait = rate_limit.seconds_until_allowed(db, identifier, ip)
    if wait:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts. Try again later.",
                            headers={"Retry-After": str(wait)})
    ok = verify_password(body.current_password, user.password_hash)
    rate_limit.record_attempt(db, identifier, ip, succeeded=ok)
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your current password is not correct.")

    user.password_hash = hash_password(body.new_password)
    user.token_version += 1          # signs out every other session
    db.commit()
    set_session_cookie(response, user)   # ...but keeps this one logged in
