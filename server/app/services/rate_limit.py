"""
Login rate limit: at most N failed attempts per account and per IP in a sliding window.

Stored in the login_attempts table (not in memory), so a restart or redeploy doesn't
reset the counters.
"""
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import LoginAttempt

KEEP_ATTEMPTS_FOR = timedelta(days=1)


def _oldest_failure_in_window(db: Session, column, value: str, since: datetime, limit: int) -> datetime | None:
    """If there are at least `limit` failures since `since`, return the oldest one counted; else None."""
    count = db.scalar(select(func.count()).select_from(LoginAttempt)
                      .where(column == value, LoginAttempt.succeeded.is_(False), LoginAttempt.attempted_at >= since))
    if count is None or count < limit:
        return None
    return db.scalar(select(func.min(LoginAttempt.attempted_at))
                     .where(column == value, LoginAttempt.succeeded.is_(False), LoginAttempt.attempted_at >= since))


def seconds_until_allowed(db: Session, identifier: str, ip: str, now: datetime | None = None) -> int:
    """0 if a login attempt is allowed now, otherwise how many seconds to wait."""
    settings = get_settings()
    now = now or datetime.now(UTC)
    window = timedelta(minutes=settings.login_window_minutes)
    since = now - window
    waits = []
    for column, value, limit in [(LoginAttempt.identifier, identifier, settings.login_max_failures_per_identifier),
                                 (LoginAttempt.ip, ip, settings.login_max_failures_per_ip)]:
        oldest = _oldest_failure_in_window(db, column, value, since, limit)
        if oldest is not None:
            waits.append(int((oldest + window - now).total_seconds()) + 1)
    return max(waits, default=0)


def record_attempt(db: Session, identifier: str, ip: str, succeeded: bool) -> None:
    db.add(LoginAttempt(identifier=identifier, ip=ip, succeeded=succeeded))
    if succeeded:
        # A successful login clears that account's failures (but not the IP's)
        db.execute(delete(LoginAttempt).where(LoginAttempt.identifier == identifier, LoginAttempt.succeeded.is_(False)))
    # Housekeeping: old rows are useless for a 15-minute window
    db.execute(delete(LoginAttempt).where(LoginAttempt.attempted_at < datetime.now(UTC) - KEEP_ATTEMPTS_FOR))
    db.commit()
