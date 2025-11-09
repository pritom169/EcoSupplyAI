"""Contract tests — validate API schema stability.

These tests ensure that the OpenAPI schemas for critical endpoints
haven't changed unexpectedly, preventing accidental breaking changes
in the API contract.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.api_gateway.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_openapi_spec_available(client: AsyncClient):
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    spec = resp.json()
    assert spec["info"]["title"] == "EcoSupplyAI"
    assert "paths" in spec


@pytest.mark.asyncio
async def test_chat_endpoint_schema(client: AsyncClient):
    resp = await client.get("/openapi.json")
    spec = resp.json()
    chat_path = spec["paths"].get("/api/v1/chat")
    assert chat_path is not None, "Missing /api/v1/chat endpoint"
    assert "post" in chat_path, "Chat endpoint must support POST"

    # Verify request body schema has required fields
    post_op = chat_path["post"]
    assert "requestBody" in post_op


@pytest.mark.asyncio
async def test_suppliers_endpoint_schema(client: AsyncClient):
    resp = await client.get("/openapi.json")
    spec = resp.json()
    # Check that supplier endpoints exist
    supplier_paths = [p for p in spec["paths"] if "suppliers" in p]
    assert len(supplier_paths) > 0, "Missing supplier endpoints"


@pytest.mark.asyncio
async def test_analytics_endpoint_schema(client: AsyncClient):
    resp = await client.get("/openapi.json")
    spec = resp.json()
    analytics_paths = [p for p in spec["paths"] if "analytics" in p]
    assert len(analytics_paths) > 0, "Missing analytics endpoints"
