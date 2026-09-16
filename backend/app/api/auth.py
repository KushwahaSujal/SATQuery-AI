"""API keys for the hosted backend (Q-021). No keys configured means auth is off, as for local runs."""
import hmac
import os
from typing import Optional, Set

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

OPEN_PATHS = {"/api/health", "/docs", "/redoc", "/openapi.json"}


def configured_keys() -> Set[str]:
    return {k.strip() for k in os.getenv("SATQUERY_API_KEYS", "").split(",") if k.strip()}


def _presented_key(request: Request) -> Optional[str]:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    # <video src> and download links cannot send headers, so media GETs pass the key as ?key=.
    return request.headers.get("x-api-key") or request.query_params.get("key")


class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        keys = configured_keys()
        if not keys or request.method == "OPTIONS" or request.url.path in OPEN_PATHS:
            return await call_next(request)
        presented = _presented_key(request)
        if presented and any(hmac.compare_digest(presented, k) for k in keys):
            return await call_next(request)
        return JSONResponse(
            status_code=401,
            content={"error": {"code": "UNAUTHORIZED", "message": "Missing or invalid API key.", "details": {}}},
        )
