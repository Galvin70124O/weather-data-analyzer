"""Favourites, recent searches, history and dashboard: correct and scoped to the user."""
import httpx
import pytest
import respx

from app.core.config import get_settings
from app.routers.my_cities import MAX_FAVORITES
from tests.conftest import register
from tests.owm_samples import current_answer, forecast_answer, geocode_answer


@pytest.fixture(autouse=True)
def owm(monkeypatch):
    monkeypatch.setenv("OPENWEATHER_API_KEY", "fake-key-for-tests-0000")
    get_settings.cache_clear()
    with respx.mock(base_url="https://api.openweathermap.org", assert_all_called=False) as router:
        router.get("/geo/1.0/direct").respond(json=geocode_answer())
        router.get("/data/2.5/weather").respond(json=current_answer())
        router.get("/data/2.5/forecast").respond(json=forecast_answer())
        yield router
    get_settings.cache_clear()


@pytest.fixture
def alice(make_client):
    browser = make_client()
    register(browser, "alice")
    return browser


@pytest.fixture
def bob(make_client):
    browser = make_client()
    register(browser, "bob")
    return browser


def city_ids(client) -> list[int]:
    return [c["id"] for c in client.get("/api/cities/search", params={"q": "London"}).json()]


def json_delete(client, url):
    return client.request("DELETE", url, json={})


# --- favourites -----------------------------------------------------------------------

def test_add_list_and_remove_favorites(alice):
    london, london_on = city_ids(alice)
    assert alice.post("/api/favorites", json={"city_id": london}).status_code == 201
    assert alice.post("/api/favorites", json={"city_id": london}).status_code == 200   # already there
    alice.post("/api/favorites", json={"city_id": london_on})
    assert [f["city"]["label"] for f in alice.get("/api/favorites").json()] == ["London, England, GB", "London, Ontario, CA"]

    assert json_delete(alice, f"/api/favorites/{london}").status_code == 204
    assert json_delete(alice, f"/api/favorites/{london}").status_code == 404
    assert [f["city"]["id"] for f in alice.get("/api/favorites").json()] == [london_on]


def test_favorite_for_unknown_city(alice):
    assert alice.post("/api/favorites", json={"city_id": 424242}).status_code == 404


def test_favorites_limit(alice, db):
    from app.models import City

    db.add_all([City(name=f"Town {i}", country="GB", lat=i / 10, lon=i / 10) for i in range(MAX_FAVORITES + 1)])
    db.commit()
    ids = [c.id for c in db.query(City).order_by(City.id)]
    for city_id in ids[:MAX_FAVORITES]:
        assert alice.post("/api/favorites", json={"city_id": city_id}).status_code == 201
    assert alice.post("/api/favorites", json={"city_id": ids[MAX_FAVORITES]}).status_code == 409


def test_favorites_are_private(alice, bob):
    london, _ = city_ids(alice)
    alice.post("/api/favorites", json={"city_id": london})
    assert bob.get("/api/favorites").json() == []
    assert json_delete(bob, f"/api/favorites/{london}").status_code == 404   # can't remove alice's
    assert len(alice.get("/api/favorites").json()) == 1


# --- recent searches + history ---------------------------------------------------------

def test_recent_searches_newest_first_and_private(alice, bob):
    london, london_on = city_ids(alice)
    alice.get(f"/api/cities/{london}/weather")
    alice.get(f"/api/cities/{london_on}/weather")
    alice.get(f"/api/cities/{london}/weather")                 # opened again: moves back to the top
    assert [r["city"]["id"] for r in alice.get("/api/searches/recent").json()] == [london, london_on]
    assert bob.get("/api/searches/recent").json() == []

    assert json_delete(alice, "/api/searches/recent").status_code == 204
    assert alice.get("/api/searches/recent").json() == []


def test_history_is_private_and_filterable(alice, bob, owm):
    london, london_on = city_ids(alice)
    alice.get(f"/api/cities/{london}/weather")
    owm.get("/data/2.5/weather").respond(json=current_answer(dt=1_761_200_000, temp=9.5))
    alice.get(f"/api/cities/{london_on}/weather")
    assert len(alice.get("/api/history").json()) == 2
    only_ontario = alice.get("/api/history", params={"city_id": london_on}).json()
    assert [h["temp_c"] for h in only_ontario] == [9.5]
    assert bob.get("/api/history").json() == []
    assert bob.get("/api/history", params={"city_id": london}).json() == []


# --- dashboard ------------------------------------------------------------------------

def test_dashboard(alice, owm):
    london, london_on = city_ids(alice)
    alice.post("/api/favorites", json={"city_id": london})
    alice.post("/api/favorites", json={"city_id": london_on})
    alice.get(f"/api/cities/{london}/weather")
    body = alice.get("/api/dashboard").json()
    assert body["username"] == "alice"
    assert [card["weather"]["temp_c"] for card in body["favorites"]] == [14.2, 14.2]
    assert [r["city"]["id"] for r in body["recent"]] == [london]       # viewing the dashboard isn't a "search"


def test_dashboard_card_shows_an_error_when_the_api_is_down(alice, owm):
    london, _ = city_ids(alice)
    alice.post("/api/favorites", json={"city_id": london})
    owm.get("/data/2.5/weather").mock(side_effect=httpx.ConnectError("down"))
    card = alice.get("/api/dashboard").json()["favorites"][0]
    assert card["weather"] is None and "unavailable" in card["error"]


def test_dashboard_is_private(alice, bob):
    london, _ = city_ids(alice)
    alice.post("/api/favorites", json={"city_id": london})
    assert bob.get("/api/dashboard").json()["favorites"] == []
