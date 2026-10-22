from datetime import UTC, datetime, timedelta

from sqlalchemy import update

from app.core.config import get_settings
from app.models import LoginAttempt
from tests.conftest import register

SETTINGS = get_settings()


def fail(client, identifier="alice"):
    return client.post("/api/auth/login", json={"identifier": identifier, "password": "wrong password"})


def test_account_is_locked_after_too_many_failures(make_client):
    register(make_client())
    attacker = make_client()
    for _ in range(SETTINGS.login_max_failures_per_identifier):
        assert fail(attacker).status_code == 401
    blocked = attacker.post("/api/auth/login", json={"identifier": "alice", "password": "correct horse 1"})
    assert blocked.status_code == 429                      # even the right password is refused for now
    assert int(blocked.headers["Retry-After"]) > 0
    assert "Too many failed logins" in blocked.json()["detail"]


def test_lock_applies_to_every_spelling_of_the_account(make_client):
    register(make_client())
    for spelling in ["alice", "ALICE", "Alice", "alice ", " alice"]:
        fail(make_client(), spelling)
    assert fail(make_client(), "aLiCe").status_code == 429


def test_lock_expires_after_the_window(make_client, db):
    register(make_client())
    for _ in range(SETTINGS.login_max_failures_per_identifier):
        fail(make_client())
    # Pretend the failures happened just over the window ago
    long_ago = datetime.now(UTC) - timedelta(minutes=SETTINGS.login_window_minutes, seconds=5)
    db.execute(update(LoginAttempt).values(attempted_at=long_ago))
    db.commit()
    ok = make_client().post("/api/auth/login", json={"identifier": "alice", "password": "correct horse 1"})
    assert ok.status_code == 200


def test_success_resets_the_account_counter(make_client):
    register(make_client())
    for _ in range(SETTINGS.login_max_failures_per_identifier - 1):
        fail(make_client())
    assert make_client().post("/api/auth/login", json={"identifier": "alice", "password": "correct horse 1"}).status_code == 200
    for _ in range(SETTINGS.login_max_failures_per_identifier - 1):
        assert fail(make_client()).status_code == 401      # counting starts again from zero


def test_one_ip_trying_many_accounts_is_limited(make_client):
    attacker = make_client()                               # TestClient always uses the same IP ("testclient")
    for i in range(SETTINGS.login_max_failures_per_ip):
        assert fail(attacker, f"user{i}").status_code == 401
    assert fail(attacker, "someone-new").status_code == 429


def test_change_password_guesses_are_limited(client):
    register(client)
    for _ in range(SETTINGS.login_max_failures_per_identifier):
        client.post("/api/auth/change-password", json={"current_password": "guess guess", "new_password": "battery staple 2"})
    blocked = client.post("/api/auth/change-password",
                          json={"current_password": "correct horse 1", "new_password": "battery staple 2"})
    assert blocked.status_code == 429
