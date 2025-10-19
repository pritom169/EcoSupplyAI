"""Analytics routes — proxy to Forecast and Content Generator services."""

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


class ForecastRequest(BaseModel):
    supplier_id: str = Field(..., examples=["SUP-001"])
    months_ahead: int = Field(default=6, ge=1, le=24)


class ReportRequest(BaseModel):
    supplier_ids: list[str] = Field(..., examples=[["SUP-001", "SUP-002"]])
    report_type: str = Field(default="quarterly", examples=["quarterly", "annual"])
    period: str = Field(default="Q4-2025", examples=["Q4-2025"])


@router.post("/forecast/emissions")
async def forecast_emissions(
    request: ForecastRequest,
    user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict:
    with tracer.start_as_current_span("forecast.emissions") as span:
        span.set_attribute("supplier.id", request.supplier_id)
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{settings.FORECAST_SERVICE_URL}/forecast/predict",
                json=request.model_dump(),
            )
            resp.raise_for_status()
            return resp.json()


@router.post("/reports/generate")
async def generate_report(
    request: ReportRequest,
    user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict:
    with tracer.start_as_current_span("reports.generate") as span:
        span.set_attribute("report.type", request.report_type)
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{settings.CONTENT_GEN_URL}/content/report",
                json=request.model_dump(),
            )
            resp.raise_for_status()
            return resp.json()


@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{settings.CONTENT_GEN_URL}/content/reports/{report_id}")
        resp.raise_for_status()
        return resp.json()