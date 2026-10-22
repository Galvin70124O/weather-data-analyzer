"""
FastAPI application.

    uvicorn app.main:app --reload        (from the server/ folder)
"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.core.logging import configure_logging
from app.db.session import get_sessionmaker
from app.routers import analytics, auth, cities, health, me, my_cities
from app.services.cache import prune_at_startup
from app.services.errors import UpstreamError

STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    prune_at_startup(get_sessionmaker())      # delete very old cache rows once per start
    yield


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Weather Data Analyzer API", version="2.0.0", docs_url="/api/docs",
                  openapi_url="/api/openapi.json", lifespan=lifespan)

    @app.middleware("http")
    async def require_json_for_writes(request: Request, call_next) -> Response:
        """
        Cross-site request protection, on top of the SameSite=Lax cookie: a state-changing
        /api request must say Content-Type: application/json. HTML forms on other sites can only
        send form or text bodies, and a cross-site script can't send JSON without a CORS
        preflight, which this API never allows.
        """
        if request.method in STATE_CHANGING_METHODS and request.url.path.startswith("/api/"):
            content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
            if content_type != "application/json":
                return JSONResponse({"detail": "Requests that change data must send Content-Type: application/json."},
                                    status_code=415)
        return await call_next(request)

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next) -> Response:
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response

    @app.exception_handler(UpstreamError)
    async def upstream_error(request: Request, error: UpstreamError) -> JSONResponse:
        # A friendly message only: never details from the outside API (they could contain the key)
        return JSONResponse({"detail": error.public_message}, status_code=error.status_code)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(me.router)
    app.include_router(cities.router)
    app.include_router(my_cities.router)
    app.include_router(analytics.router)
    return app


app = create_app()
