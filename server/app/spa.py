"""
Serves the built React client (client/dist) from the same origin as the API, so the session
cookie needs no CORS. Registered after the API routers:

- a real file in dist (e.g. /assets/index-3f9a.js, /favicon.svg) is sent as is;
- any other path that isn't /api/... gets index.html, and React Router shows the page;
- unknown /api/... paths stay JSON 404s.

Hashed files under /assets/ never change, so browsers may keep them for a year; index.html is
never cached, so a new deploy shows up on the next load. HTML gets a strict Content-Security-Policy
that allows the one inline script in index.html (light/dark before the first paint) by its hash.
"""
import base64
import hashlib
import logging
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse, Response

log = logging.getLogger(__name__)

IMMUTABLE = "public, max-age=31536000, immutable"
NO_CACHE = "no-cache"
INLINE_SCRIPT = re.compile(r"<script>([\s\S]*?)</script>")


def content_security_policy(index_html: str) -> str:
    hashes = " ".join(
        f"'sha256-{base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()}'"
        for script in INLINE_SCRIPT.findall(index_html)
    )
    return "; ".join([
        "default-src 'self'",
        f"script-src 'self' {hashes}".strip(),
        "style-src 'self' 'unsafe-inline'",        # React style={{...}} props (chart colours, wind arrow)
        "img-src 'self' data:",                    # weather icons are data: URLs
        "font-src 'self'",
        "connect-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "object-src 'none'",
    ])


def resolve_file(dist: Path, path: str) -> Path | None:
    """The file in dist for this URL path, or None. Never anything outside dist (no ../ tricks)."""
    candidate = (dist / path).resolve()
    if candidate != dist and dist in candidate.parents and candidate.is_file():
        return candidate
    return None


def mount_client(app: FastAPI, dist: Path) -> None:
    dist = dist.resolve()
    index = dist / "index.html"
    if not index.is_file():
        log.info("No built client at %s: serving the API only (run `npm run build` in client/)", dist)
        return
    html = index.read_text(encoding="utf-8")
    html_headers = {"Cache-Control": NO_CACHE, "Content-Security-Policy": content_security_policy(html)}

    @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)   # HEAD: uptime checkers
    def client(path: str) -> Response:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")
        file = resolve_file(dist, path)
        if file is not None and file != index.resolve():
            cache = IMMUTABLE if file.parent == dist / "assets" else NO_CACHE
            return FileResponse(file, headers={"Cache-Control": cache})
        return Response(html, media_type="text/html; charset=utf-8", headers=html_headers)
