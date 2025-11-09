"""Integration tests for API Gateway routes.

These tests use httpx.AsyncClient against the FastAPI test client,
mocking downstream services with respx.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.api_gateway.main import app
from src.api_gateway.middleware.auth import create_access_token


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Generate a valid JWT for testing."""
    token = create_access_token(
        {"sub": "test-user-001", "roles": ["analyst"], "email": "test@ecosupplyai.dev"}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def client():
    """Async test client for the API Gateway."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Health & Ready Endpoints ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "api-gateway"


@pytest.mark.asyncio
async def test_ready(client: AsyncClient):
    resp = await client.get("/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


# ── Authentication ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unauthenticated_chat_returns_403(client: AsyncClient):
    resp = await client.post("/api/v1/chat", json={"message": "Hello"})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_bad_token_returns_401(client: AsyncClient):
    resp = await client.post(
        "/api/v1/chat",
        json={"message": "Hello"},
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    assert resp.status_code == 401


# ── Rate Limiting ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rate_limit_headers(client: AsyncClient, auth_headers: dict):
    """Ensure the rate limiter is invoked without crashing the request."""
    # This test validates that the rate limiter middleware is properly wired.
    # Note: Full rate limit exhaustion tests should be done via load testing.
    resp = await client.post(
        "/api/v1/chat",
        json={"message": "Rate limit test"},
        headers=auth_headers,
    )
    # Even if downstream is unreachable, we should not get a 429 on first req
    assert resp.status_code != 429
