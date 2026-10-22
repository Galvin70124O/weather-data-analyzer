"""FastAPI serves the built client: real files, index.html for app pages, never files outside dist."""
import base64
import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.spa import content_security_policy, resolve_file

SCRIPT = "document.documentElement.classList.add('dark');"
INDEX = f"<!doctype html><html><head><script>{SCRIPT}</script></head><body><div id=root></div></body></html>"


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    folder = tmp_path / "dist"
    (folder / "assets").mkdir(parents=True)
    (folder / "index.html").write_text(INDEX, encoding="utf-8")
    (folder / "assets" / "index-abc123.js").write_text("console.log('app')", encoding="utf-8")
    (folder / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("not for the web", encoding="utf-8")     # next to dist, not in it
    return folder


@pytest.fixture
def web(dist: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("CLIENT_DIST", str(dist))
    get_settings.cache_clear()
    yield TestClient(create_app())
    get_settings.cache_clear()


def test_app_pages_get_index_html_with_a_strict_csp(web):
    for path in ["/", "/cities/3", "/compare?ids=1,2", "/account"]:
        response = web.get(path)
        assert response.status_code == 200
        assert response.text == INDEX
        assert response.headers["cache-control"] == "no-cache"
        csp = response.headers["content-security-policy"]
        assert "default-src 'self'" in csp and "frame-ancestors 'none'" in csp
        assert "'unsafe-inline'" not in csp.split("script-src")[1].split(";")[0]
    assert web.head("/cities/3").status_code == 200


def test_the_inline_script_is_allowed_by_its_hash():
    digest = base64.b64encode(hashlib.sha256(SCRIPT.encode()).digest()).decode()
    assert f"script-src 'self' 'sha256-{digest}'" in content_security_policy(INDEX)


def test_built_files_are_served_and_hashed_assets_cached_for_good(web):
    asset = web.get("/assets/index-abc123.js")
    assert asset.status_code == 200 and asset.text == "console.log('app')"
    assert asset.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert web.get("/favicon.svg").headers["cache-control"] == "no-cache"


def test_unknown_api_paths_stay_json_404s(web):
    response = web.get("/api/nope")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}
    assert web.get("/api/health").status_code in (200, 503)       # real API routes still win


def test_no_files_outside_dist(web, dist):
    for path in ["/../secret.txt", "/%2e%2e/secret.txt", "/assets/../../secret.txt"]:
        assert "not for the web" not in web.get(path).text
    assert resolve_file(dist, "../secret.txt") is None
    assert resolve_file(dist, "assets/../index.html") == (dist / "index.html").resolve()


def test_without_a_build_only_the_api_is_served(tmp_path, monkeypatch):
    monkeypatch.setenv("CLIENT_DIST", str(tmp_path / "missing"))
    get_settings.cache_clear()
    try:
        assert TestClient(create_app()).get("/cities/3").status_code == 404
    finally:
        get_settings.cache_clear()


def test_hsts_only_in_production(monkeypatch, dist):
    monkeypatch.setenv("CLIENT_DIST", str(dist))
    get_settings.cache_clear()
    try:
        assert "strict-transport-security" not in TestClient(create_app()).get("/").headers
        monkeypatch.setenv("ENVIRONMENT", "production")
        get_settings.cache_clear()
        assert TestClient(create_app()).get("/").headers["strict-transport-security"].startswith("max-age=")
    finally:
        get_settings.cache_clear()
