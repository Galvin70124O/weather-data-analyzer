"""
FastAPI application.

    uvicorn app.main:app --reload        (from the server/ folder)
"""
from fastapi import FastAPI, Request, Response

from app.routers import auth, health, me

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


def create_app() -> FastAPI:
    app = FastAPI(title="Weather Data Analyzer API", version="2.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json")

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next) -> Response:
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(me.router)
    return app


app = create_app()
