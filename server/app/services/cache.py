"""
Cache for outside API answers, in the api_cache table.

cached_fetch(db, key, ttl, fetch):
  - fresh row       -> return it (no API call)
  - missing/expired -> call fetch(), store the answer for `ttl` seconds, return it
  - fetch() fails   -> return the expired row marked stale=True if there is one, else re-raise
"""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import ApiCache
from app.services.errors import UpstreamError, UpstreamNotFound

# Expired rows are kept as a fallback for this long, then deleted
KEEP_EXPIRED_FOR = timedelta(days=30)


@dataclass(frozen=True)
class CachedResult:
    data: Any
    fetched_at: datetime
    stale: bool          # True = the API failed and this is an older, expired answer


def cached_fetch(db: Session, key: str, ttl_seconds: int, fetch: Callable[[], Any],
                 now: datetime | None = None) -> CachedResult:
    now = now or datetime.now(UTC)
    row = db.get(ApiCache, key)
    if row is not None and row.expires_at > now:
        return CachedResult(row.payload, row.fetched_at, stale=False)

    try:
        data = fetch()
    except UpstreamNotFound:
        raise                 # "this place doesn't exist" is a real answer, not an outage
    except UpstreamError:
        if row is not None:
            return CachedResult(row.payload, row.fetched_at, stale=True)
        raise

    store(db, key, data, ttl_seconds, now)
    return CachedResult(data, now, stale=False)


def store(db: Session, key: str, data: Any, ttl_seconds: int, now: datetime) -> None:
    values = {"key": key, "payload": data, "fetched_at": now, "expires_at": now + timedelta(seconds=ttl_seconds)}
    statement = insert(ApiCache).values(**values)
    db.execute(statement.on_conflict_do_update(index_elements=[ApiCache.key],
                                               set_={k: v for k, v in values.items() if k != "key"}))
    db.execute(delete(ApiCache).where(ApiCache.expires_at < now - KEEP_EXPIRED_FOR))
    db.commit()

