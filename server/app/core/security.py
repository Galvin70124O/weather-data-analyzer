"""Password hashing (bcrypt) and session tokens (JWT)."""
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import get_settings

BCRYPT_ROUNDS = 12
# bcrypt only looks at the first 72 bytes of a password, so longer ones are rejected up front
MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:   # malformed hash
        return False


# Used when the user doesn't exist, so a failed login takes as long as a wrong password
# (otherwise response times would reveal which usernames exist)
_DUMMY_HASH = hash_password("timing-safety-dummy-password")


def verify_dummy_password(password: str) -> None:
    verify_password(password, _DUMMY_HASH)


def create_session_token(user_id: int, token_version: int, now: datetime | None = None) -> str:
    settings = get_settings()
    issued = now or datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "tv": token_version,            # bumped on password change -> old tokens stop working
        "iat": int(issued.timestamp()),
        "exp": int((issued + timedelta(days=settings.jwt_expire_days)).timestamp()),
    }
    return jwt.encode(claims, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithm)


def decode_session_token(token: str) -> tuple[int, int] | None:
    """Return (user_id, token_version), or None if the token is invalid or expired."""
    settings = get_settings()
    try:
        claims = jwt.decode(token, settings.jwt_secret.get_secret_value(), algorithms=[settings.jwt_algorithm],
                            options={"require": ["sub", "tv", "exp"]})
        return int(claims["sub"]), int(claims["tv"])
    except (jwt.PyJWTError, ValueError, TypeError):
        return None
