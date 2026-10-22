"""
App settings, read from environment variables (and the repo-root .env file locally).

On Render every value comes from the dashboard / render.yaml; locally from .env.
Never put real secrets in code or in .env.example.
"""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


def normalize_database_url(url: str) -> str:
    """Neon and Render give "postgres://" or "postgresql://" URLs; SQLAlchemy needs the psycopg driver name."""
    url = url.strip()
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    # The built React client (npm run build). Served by FastAPI when it exists; absent in dev/tests.
    client_dist: Path = REPO_ROOT / "client" / "dist"

    database_url: str
    test_database_url: str | None = None

    # Auth
    jwt_secret: SecretStr
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7
    cookie_name: str = "wa_session"
    # None = follow ENVIRONMENT (Secure in production, not over local http). Can be forced on locally.
    cookie_secure: bool | None = None

    # OpenWeatherMap (current weather, forecast, geocoding). Server-side only: never sent to the browser.
    openweather_api_key: SecretStr | None = None
    openweather_base_url: str = "https://api.openweathermap.org"
    http_timeout_seconds: float = 6.0

    # How long outside API answers are cached (seconds)
    cache_ttl_geocode: int = 7 * 24 * 3600
    cache_ttl_current: int = 10 * 60
    cache_ttl_forecast: int = 60 * 60

    # Login rate limit: failed attempts allowed in a sliding window
    login_window_minutes: int = 15
    login_max_failures_per_identifier: int = 5
    login_max_failures_per_ip: int = 20

    @field_validator("database_url", "test_database_url")
    @classmethod
    def _normalize_url(cls, value: str | None) -> str | None:
        return normalize_database_url(value) if value else value

    @field_validator("openweather_api_key", mode="before")
    @classmethod
    def _empty_key_means_not_set(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("jwt_secret")
    @classmethod
    def _secret_long_enough(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters (generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\")")
        return value

    @model_validator(mode="after")
    def _production_cookie_is_secure(self) -> "Settings":
        if self.environment == "production" and self.cookie_secure is False:
            raise ValueError("COOKIE_SECURE=false is not allowed in production: the session cookie must be HTTPS-only.")
        return self

    @property
    def secure_cookies(self) -> bool:
        """Whether the session cookie gets the Secure flag (only sent over HTTPS)."""
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
