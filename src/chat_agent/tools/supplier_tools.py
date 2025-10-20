"""Semantic Kernel function definitions for supplier chain tools."""

from __future__ import annotations

from typing import Annotated

import httpx
from semantic_kernel.functions import kernel_function

from src.chat_agent.config import get_chat_settings


class SupplierPlugin:
    """Plugin exposing supply chain tools to the Semantic Kernel agent."""

    def __init__(self) -> None:
        self.settings = get_chat_settings()

    @kernel_function(name="search_regulations", description="Search EU sustainability regulations and compliance documents")
    async def search_regulations(
        self,
        query: Annotated[str, "The search query about regulations or compliance"],
    ) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.settings.RAG_SERVICE_URL}/rag/query",
                json={"question": query, "top_k": 5},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("answer", "No results found.")

    @kernel_function(name="get_esg_score", description="Get the ESG risk score for a specific supplier")
    async def get_esg_score(
        self,
        supplier_id: Annotated[str, "The supplier ID (e.g., SUP-001)"],
    ) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.settings.SCORING_SERVICE_URL}/scoring/esg",
                json={"supplier_id": supplier_id},
            )
            resp.raise_for_status()
            return str(resp.json())

    @kernel_function(name="forecast_emissions", description="Predict future Scope 3 emissions for a supplier")
    async def forecast_emissions(
        self,
        supplier_id: Annotated[str, "The supplier ID"],
        months_ahead: Annotated[int, "Number of months to forecast"] = 6,
    ) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.settings.FORECAST_SERVICE_URL}/forecast/predict",
                json={"supplier_id": supplier_id, "months_ahead": months_ahead},
            )
            resp.raise_for_status()
            return str(resp.json())

    @kernel_function(name="search_supplier_database", description="Look up supplier information by name or ID")
    async def search_supplier_database(
        self,
        query: Annotated[str, "Supplier name or ID to search for"],
    ) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.settings.SCORING_SERVICE_URL}/scoring/suppliers",
                params={"query": query},
            )
            resp.raise_for_status()
            return str(resp.json())

    @kernel_function(name="generate_report", description="Trigger generation of a sustainability report")
    async def generate_report(
        self,
        supplier_ids: Annotated[str, "Comma-separated supplier IDs"],
        report_type: Annotated[str, "Report type: quarterly or annual"] = "quarterly",
    ) -> str:
        ids = [s.strip() for s in supplier_ids.split(",")]
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "http://localhost:8005/content/report",
                json={"supplier_ids": ids, "report_type": report_type},
            )
            resp.raise_for_status()
            return str(resp.json())
