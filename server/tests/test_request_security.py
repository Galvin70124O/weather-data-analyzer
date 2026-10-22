"""Secure cookie in production, and cross-site request protection (JSON-only writes)."""
from contextlib import contextmanager

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from tests.conftest import register


@contextmanager
def environment(monkeypatch, **values):
    """Run with different settings, then put the normal ones back."""
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    try:
        yield
    finally:
        for name in values:
            monkeypatch.delenv(name, raising=False)
        get_settings.cache_clear()


# --- Secure cookie -----------------------------------------------------------------------

def test_cookie_is_not_secure_for_local_http(client):
    assert "Secure" not in register(client).headers["set-cookie"]


def test_cookie_is_secure_in_production(client, monkeypatch):
    with environment(monkeypatch, ENVIRONMENT="production"):
        cookie = register(client).headers["set-cookie"]
        logout_cookie = client.post("/api/auth/logout", json={}).headers["set-cookie"]
    assert "Secure" in cookie and "HttpOnly" in cookie
    assert "Secure" in logout_cookie


def test_secure_can_be_forced_on_locally(client, monkeypatch):
    with environment(monkeypatch, COOKIE_SECURE="true"):
        assert "Secure" in register(client).headers["set-cookie"]


def test_production_refuses_an_insecure_cookie():
    with pytest.raises(ValidationError, match="COOKIE_SECURE=false is not allowed in production"):
        Settings(environment="production", cookie_secure=False,
                 database_url="postgresql://u@h/db", jwt_secret="x" * 40, _env_file=None)
    assert Settings(environment="production", database_url="postgresql://u@h/db",
                    jwt_secret="x" * 40, _env_file=None).secure_cookies is True


# --- JSON-only writes -------------------------------------------------------------------

@pytest.mark.parametrize("content_type", ["application/x-www-form-urlencoded", "multipart/form-data; boundary=x",
                                          "text/plain", None])
def test_writes_without_json_are_rejected(client, content_type):
    headers = {"Content-Type": content_type} if content_type else {}
    body = "username=eve&email=eve@example.com&password=longenough"
    response = client.post("/api/auth/register", content=body, headers=headers)
    assert response.status_code == 415
    assert "application/json" in response.json()["detail"]


def test_rejected_before_anything_happens(client, db):
    from app.models import User

    client.post("/api/auth/register", content='{"username":"eve","email":"eve@example.com","password":"longenough"}',
                headers={"Content-Type": "text/plain"})
    assert db.query(User).count() == 0                 # the JSON-looking text body was not processed


def test_every_write_method_is_covered(client):
    register(client)
    for method in ["POST", "PUT", "PATCH", "DELETE"]:
        response = client.request(method, "/api/me", content="units=imperial",
                                  headers={"Content-Type": "application/x-www-form-urlencoded"})
        assert response.status_code == 415, method
    assert client.get("/api/me").json()["units"] == "metric"   # nothing changed


def test_logout_needs_json_too(client):
    register(client)
    assert client.post("/api/auth/logout").status_code == 415
    assert client.get("/api/me").status_code == 200    # still logged in


def test_json_with_charset_and_reads_are_allowed(client):
    response = client.post("/api/auth/register",
                           content='{"username":"eve","email":"eve@example.com","password":"longenough"}',
                           headers={"Content-Type": "application/json; charset=utf-8"})
    assert response.status_code == 201
    assert client.get("/api/me").status_code == 200    # GET needs no content type
