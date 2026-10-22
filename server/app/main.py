"""
FastAPI application.

    uvicorn app.main:app --reload        (from the server/ folder)
"""
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.routers import auth, health, me

STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


def create_app() -> FastAPI:
    app = FastAPI(title="Weather Data Analyzer API", version="2.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json")

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

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(me.router)
    return app


app = create_app()
