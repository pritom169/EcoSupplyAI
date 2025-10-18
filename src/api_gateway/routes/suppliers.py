"""Supplier routes — proxy to Scoring and Workflow services."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from opentelemetry import trace
from pydantic import BaseModel, Field

from src.api_gateway.config import Settings, get_settings
from src.api_gateway.middleware.auth import get_current_user

import httpx

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)
router = APIRouter()


class OnboardRequest(BaseModel):
    supplier_name: str = Field(..., examples=["GreenTex GmbH"])
    country: str = Field(..., examples=["Germany"])
    industry: str = Field(..., examples=["Textiles & Apparel"])
    contact_email: str = Field(..., examples=["contact@greentex.de"])


@router.get("/suppliers")
async def list_suppliers(
    user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict:
    with tracer.start_as_current_span("suppliers.list"):
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{settings.SCORING_SERVICE_URL}/scoring/suppliers")
            resp.raise_for_status()
            return resp.json()


@router.get("/suppliers/{supplier_id}")
async def get_supplier(
    supplier_id: str,
    user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict:
    with tracer.start_as_current_span("suppliers.get") as span:
        span.set_attribute("supplier.id", supplier_id)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{settings.SCORING_SERVICE_URL}/scoring/suppliers/{supplier_id}")
            resp.raise_for_status()
            return resp.json()


@router.get("/suppliers/{supplier_id}/score")
async def get_supplier_score(
    supplier_id: str,
    user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict:
    with tracer.start_as_current_span("suppliers.score") as span:
        span.set_attribute("supplier.id", supplier_id)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.SCORING_SERVICE_URL}/scoring/esg",
                json={"supplier_id": supplier_id},
            )
            resp.raise_for_status()
            return resp.json()


@router.post("/suppliers/{supplier_id}/onboard")
async def onboard_supplier(
    supplier_id: str,
    request: OnboardRequest,
    user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict:
    with tracer.start_as_current_span("suppliers.onboard") as span:
        span.set_attribute("supplier.id", supplier_id)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.WORKFLOW_ENGINE_URL}/workflows/start/supplier_onboarding",
                json={
                    "supplier_id": supplier_id,
                    "supplier_name": request.supplier_name,
                    "country": request.country,
                    "industry": request.industry,
                    "contact_email": request.contact_email,
                    "initiated_by": user["user_id"],
                },
            )
            resp.raise_for_status()
            return resp.json()