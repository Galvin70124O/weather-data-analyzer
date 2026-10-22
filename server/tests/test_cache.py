"""api_cache: cached_fetch behaviour and the clean-up of old rows."""
from datetime import UTC, datetime, timedelta

import pytest

from app.models import ApiCache
from app.services import cache
from app.services.errors import UpstreamError, UpstreamNotFound

NOW = datetime(2026, 10, 22, 12, tzinfo=UTC)


@pytest.fixture(autouse=True)
def reset_prune_clock():
    cache._last_prune = None
    yield
    cache._last_prune = None


def add_row(db, key, expired_ago=None, expires_in=None):
    expires = NOW - expired_ago if expired_ago is not None else NOW + expires_in
    db.add(ApiCache(key=key, payload={"k": key}, fetched_at=expires - timedelta(minutes=10), expires_at=expires))
    db.commit()


def keys(db):
    db.expire_all()
    return sorted(row.key for row in db.query(ApiCache))


# --- clean-up -----------------------------------------------------------------------------

def test_prune_deletes_only_rows_older_than_the_stale_window(db):
    add_row(db, "fresh", expires_in=timedelta(minutes=5))
    add_row(db, "recently-expired", expired_ago=timedelta(days=3))          # still useful as a stale fallback
    add_row(db, "ancient", expired_ago=cache.KEEP_EXPIRED_FOR + timedelta(hours=1))
    assert cache.prune_expired(db, NOW) == 1
    assert keys(db) == ["fresh", "recently-expired"]


def test_prune_is_throttled(db):
    assert cache.maybe_prune(db, NOW) is True
    add_row(db, "ancient", expired_ago=cache.KEEP_EXPIRED_FOR + timedelta(days=1))
    assert cache.maybe_prune(db, NOW + timedelta(minutes=5)) is False       # too soon: only a time check
    assert keys(db) == ["ancient"]
    assert cache.maybe_prune(db, NOW + cache.PRUNE_EVERY) is True
    assert keys(db) == []


def test_writes_trigger_the_periodic_clean_up(db):
    add_row(db, "ancient", expired_ago=cache.KEEP_EXPIRED_FOR + timedelta(days=1))
    cache.cached_fetch(db, "new", 60, lambda: {"v": 1}, now=NOW)
    assert keys(db) == ["new"]


def test_prune_at_startup(session_factory, db):
    add_row(db, "ancient", expired_ago=timedelta(days=400))
    cache.prune_at_startup(session_factory)
    assert keys(db) == []


def test_prune_at_startup_never_crashes(caplog):
    def broken_factory():
        raise ConnectionError("database is down")

    cache.prune_at_startup(broken_factory)                                  # no exception
    assert "skipped" in caplog.text


# --- cached_fetch ---------------------------------------------------------------------------

def test_fresh_hit_does_not_call_the_api(db):
    add_row(db, "k", expires_in=timedelta(minutes=5))
    result = cache.cached_fetch(db, "k", 60, lambda: pytest.fail("should not be called"), now=NOW)
    assert result.data == {"k": "k"} and result.stale is False


def test_failure_with_an_expired_row_is_stale(db):
    add_row(db, "k", expired_ago=timedelta(minutes=5))

    def down():
        raise UpstreamError()

    result = cache.cached_fetch(db, "k", 60, down, now=NOW)
    assert result.stale is True and result.data == {"k": "k"}


def test_not_found_is_never_hidden_behind_stale_data(db):
    add_row(db, "k", expired_ago=timedelta(minutes=5))

    def gone():
        raise UpstreamNotFound()

    with pytest.raises(UpstreamNotFound):
        cache.cached_fetch(db, "k", 60, gone, now=NOW)
