"""One shared httpx client for outside APIs (keeps connections open between requests)."""
from functools import lru_cache

import httpx

from app.core.config import get_settings


@lru_cache
def get_http_client() -> httpx.Client:
    timeout = get_settings().http_timeout_seconds
    return httpx.Client(
        timeout=httpx.Timeout(timeout, connect=min(3.0, timeout)),
        headers={"User-Agent": "weather-data-analyzer/2.0"},
    )
