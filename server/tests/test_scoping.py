"""
Every query is scoped to the logged-in user.

1. Every /api route needs a login, except a short public allowlist. New routes are covered
   automatically: if someone adds a route and forgets CurrentUser, this test fails.
2. Two users never see or change each other's data.
"""
import re

import pytest
from fastapi.routing import APIRoute

from app.main import create_app
from tests.conftest import register

PUBLIC_ROUTES = {
    ("GET", "/api/health"),
    ("POST", "/api/auth/register"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/logout"),
}


def api_routes():
    for route in create_app().routes:
        if isinstance(route, APIRoute) and route.path.startswith("/api") and not route.path.startswith("/api/docs"):
            for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
                yield method, route.path


@pytest.mark.parametrize("method, path", sorted(set(api_routes()) - PUBLIC_ROUTES))
def test_private_routes_need_a_login(client, method, path):
    url = re.sub(r"\{[^}]+\}", "1", path)                  # fill path parameters with a dummy id
    response = client.request(method, url, json={})
    assert response.status_code == 401, f"{method} {path} answered {response.status_code} without a login"


def test_allowlist_only_contains_real_routes():
    assert PUBLIC_ROUTES <= set(api_routes())


def test_users_only_see_their_own_account(make_client):
    alice, bob = make_client(), make_client()
    register(alice, "alice")
    register(bob, "bob")
    alice.patch("/api/me", json={"units": "imperial"})

    assert alice.get("/api/me").json()["username"] == "alice"
    assert bob.get("/api/me").json()["username"] == "bob"
    assert bob.get("/api/me").json()["units"] == "metric"   # alice's change didn't touch bob


def test_a_token_for_a_deleted_user_stops_working(make_client, db):
    from app.models import User

    alice = make_client()
    register(alice)
    db.query(User).delete()
    db.commit()
    assert alice.get("/api/me").status_code == 401
