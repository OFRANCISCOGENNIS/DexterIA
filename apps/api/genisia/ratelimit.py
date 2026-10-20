"""Limitador de requisições em memória (janela deslizante por cliente).

Suficiente para uma instância única. Para várias instâncias, substituir por Redis.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .config import settings


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window: float = 60.0) -> tuple[bool, float]:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > window:
                hits.popleft()
            if len(hits) >= limit:
                return False, window - (now - hits[0])
            hits.append(now)
            return True, 0.0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = SlidingWindowLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api/") or path == "/api/health":
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        auth = request.headers.get("authorization", "")
        key_base = auth[-24:] if auth else client
        if path.startswith("/api/auth/"):
            allowed, retry = limiter.allow(f"auth:{client}", settings.auth_rate_limit_per_minute)
        else:
            allowed, retry = limiter.allow(f"api:{key_base}", settings.rate_limit_per_minute)
        if not allowed:
            return JSONResponse(
                {"detail": "Limite de requisições excedido. Tente novamente em instantes."},
                status_code=429,
                headers={"Retry-After": str(int(retry) + 1)},
            )
        return await call_next(request)
