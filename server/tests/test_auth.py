from app.core.config import get_settings
from app.models import User
from tests.conftest import register

COOKIE = get_settings().cookie_name


# --- register ------------------------------------------------------------------------

def test_register_logs_you_in_with_an_httponly_cookie(client):
    response = register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "alice" and body["email"] == "alice@example.com" and body["units"] == "metric"
    assert "password" not in str(body)
    cookie = response.headers["set-cookie"]
    assert f"{COOKIE}=" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie
    assert client.get("/api/me").json()["username"] == "alice"


def test_password_is_stored_as_bcrypt(client, db):
    register(client)
    stored = db.query(User).one().password_hash
    assert stored.startswith("$2b$12$") and "correct horse" not in stored


def test_username_and_email_are_unique_ignoring_case(client):
    assert register(client, "alice").status_code == 201
    assert register(client, "ALICE", email="other@example.com").status_code == 409
    assert register(client, "bob", email="Alice@Example.com").status_code == 409


def test_register_validation(client):
    assert register(client, "al").status_code == 422                      # too short
    assert register(client, "bob@example.com").status_code == 422         # no "@" in usernames
    assert register(client, "bob", password="short").status_code == 422   # < 8 characters
    assert register(client, "bob", password="é" * 37).status_code == 422   # 74 bytes > bcrypt's 72
    assert client.post("/api/auth/register", json={"username": "bob", "email": "nope", "password": "longenough"}).status_code == 422


# --- login / logout ------------------------------------------------------------------

def test_login_with_username_or_email(make_client):
    register(make_client())
    for identifier in ["alice", "ALICE", "alice@example.com", " Alice@Example.com "]:
        browser = make_client()
        response = browser.post("/api/auth/login", json={"identifier": identifier, "password": "correct horse 1"})
        assert response.status_code == 200, identifier
        assert browser.get("/api/me").json()["username"] == "alice"


def test_wrong_password_and_unknown_user_get_the_same_message(make_client):
    register(make_client())
    wrong = make_client().post("/api/auth/login", json={"identifier": "alice", "password": "nope nope"})
    unknown = make_client().post("/api/auth/login", json={"identifier": "nobody", "password": "nope nope"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": "Invalid username/email or password."}


def test_logout_clears_the_cookie(client):
    register(client)
    response = client.post("/api/auth/logout")
    assert response.status_code == 204
    assert f'{COOKIE}=""' in response.headers["set-cookie"] or "Max-Age=0" in response.headers["set-cookie"]
    assert client.get("/api/me").status_code == 401


def test_tampered_or_garbage_cookie_is_rejected(client):
    register(client)
    token = client.cookies.get(COOKIE)
    client.cookies.set(COOKIE, token[:-2] + ("aa" if not token.endswith("aa") else "bb"))
    assert client.get("/api/me").status_code == 401
    client.cookies.set(COOKIE, "not-a-jwt")
    assert client.get("/api/me").status_code == 401


# --- change password -----------------------------------------------------------------

def test_change_password_signs_out_other_sessions(make_client):
    laptop, phone = make_client(), make_client()
    register(laptop)
    phone.post("/api/auth/login", json={"identifier": "alice", "password": "correct horse 1"})
    assert phone.get("/api/me").status_code == 200

    response = laptop.post("/api/auth/change-password",
                           json={"current_password": "correct horse 1", "new_password": "battery staple 2"})
    assert response.status_code == 204
    assert laptop.get("/api/me").status_code == 200      # this session stays logged in
    assert phone.get("/api/me").status_code == 401       # the other one is signed out

    fresh = make_client()
    assert fresh.post("/api/auth/login", json={"identifier": "alice", "password": "correct horse 1"}).status_code == 401
    assert fresh.post("/api/auth/login", json={"identifier": "alice", "password": "battery staple 2"}).status_code == 200


def test_change_password_needs_the_current_password(client):
    register(client)
    response = client.post("/api/auth/change-password",
                           json={"current_password": "wrong one", "new_password": "battery staple 2"})
    assert response.status_code == 400
    assert client.post("/api/auth/change-password",
                       json={"current_password": "correct horse 1", "new_password": "short"}).status_code == 422


# --- preferences -----------------------------------------------------------------------

def test_units_preference_is_saved_on_the_account(make_client):
    laptop = make_client()
    register(laptop)
    assert laptop.patch("/api/me", json={"units": "imperial"}).json()["units"] == "imperial"
    phone = make_client()
    phone.post("/api/auth/login", json={"identifier": "alice", "password": "correct horse 1"})
    assert phone.get("/api/me").json()["units"] == "imperial"     # follows the account
    assert laptop.patch("/api/me", json={"units": "kelvin"}).status_code == 422
