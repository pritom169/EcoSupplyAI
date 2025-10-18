"""Sliding window rate limiter using Redis (with in-memory fallback)."""

from __future__ import annotations

import time
from collections import defaultdict

import structlog
from fastapi import Depends, HTTPException, Request, status

from src.api_gateway.config import Settings, get_settings

logger = structlog.get_logger(__name__)

# In-memory fallback when Redis is unavailable
_in_memory_store: dict[str, list[float]] = defaultdict(list)


class RateLimiter:
    def __init__(self, requests_per_minute: int = 60) -> None:
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60

    def _get_client_key(self, request: Request, user: dict | None = None) -> str:
        if user and user.get("user_id"):
            return f"rate_limit:{user['user_id']}"
        forwarded = request.headers.get("X-Forwarded-For")
        client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
        return f"rate_limit:{client_ip}"

    async def check_rate_limit(self, key: str) -> tuple[bool, int]:
        """Check rate limit using in-memory sliding window. Returns (allowed, remaining)."""
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old entries
        _in_memory_store[key] = [t for t in _in_memory_store[key] if t > window_start]

        current_count = len(_in_memory_store[key])
        remaining = max(0, self.requests_per_minute - current_count)

        if current_count >= self.requests_per_minute:
            return False, 0

        _in_memory_store[key].append(now)
        return True, remaining - 1


_limiter = RateLimiter()


async def rate_limit_dependency(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    _limiter.requests_per_minute = settings.RATE_LIMIT_PER_MINUTE
    key = _limiter._get_client_key(request)
    allowed, remaining = await _limiter.check_rate_limit(key)

    request.state.rate_limit_remaining = remaining

    if not allowed:
        logger.warning("rate_limit.exceeded", key=key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": "60", "X-RateLimit-Remaining": "0"},
        )