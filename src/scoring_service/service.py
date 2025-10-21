"""Scoring Service FastAPI — ESG risk scoring and supplier benchmarking."""

from __future__ import annotations

import json
from pathlib import Path

import structlog
from fastapi import FastAPI, HTTPException
from opentelemetry import trace
from pydantic import BaseModel, Field

from src.scoring_service.models.esg_scorer import ESGScorer

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)
app = FastAPI(title="EcoSupplyAI Scoring Service", version="0.1.0")

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "sample" / "suppliers.json"
scorer = ESGScorer()


def _load_suppliers() -> dict[str, dict]:
    if DATA_PATH.exists():
        data = json.loads(DATA_PATH.read_text())
        return {s["id"]: s for s in data.get("suppliers", [])}
    return {}


class ESGRequest(BaseModel):
    supplier_id: str = Field(..., examples=["SUP-001"])


class BatchESGRequest(BaseModel):
    supplier_ids: list[str]


@app.post("/scoring/esg")
async def calculate_esg_score(request: ESGRequest) -> dict:
    with tracer.start_as_current_span("scoring.esg") as span:
        span.set_attribute("supplier.id", request.supplier_id)
        suppliers = _load_suppliers()
        supplier = suppliers.get(request.supplier_id)
        if not supplier:
            raise HTTPException(status_code=404, detail=f"Supplier {request.supplier_id} not found")
        result = scorer.score_supplier(supplier)
        result["supplier_id"] = request.supplier_id
        result["supplier_name"] = supplier["name"]
        return result


@app.post("/scoring/esg/batch")
async def batch_esg_score(request: BatchESGRequest) -> dict:
    suppliers = _load_suppliers()
    results = []
    for sid in request.supplier_ids:
        supplier = suppliers.get(sid)
        if supplier:
            score = scorer.score_supplier(supplier)
            score["supplier_id"] = sid
            score["supplier_name"] = supplier["name"]
            results.append(score)
    return {"scores": results}


@app.get("/scoring/benchmark/{industry}")
async def get_benchmark(industry: str) -> dict:
    suppliers = _load_suppliers()
    industry_suppliers = [s for s in suppliers.values() if s["industry"].lower() == industry.lower()]
    if not industry_suppliers:
        raise HTTPException(status_code=404, detail=f"No suppliers found for industry: {industry}")

    scores = [scorer.score_supplier(s)["composite_score"] for s in industry_suppliers]
    return {
        "industry": industry,
        "supplier_count": len(industry_suppliers),
        "avg_score": round(sum(scores) / len(scores), 1),
        "min_score": min(scores),
        "max_score": max(scores),
    }


@app.get("/scoring/explain/{supplier_id}")
async def explain_score(supplier_id: str) -> dict:
    suppliers = _load_suppliers()
    supplier = suppliers.get(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")
    result = scorer.score_supplier(supplier)
    result["supplier_id"] = supplier_id
    result["supplier_name"] = supplier["name"]
    return result


@app.get("/scoring/suppliers")
async def list_suppliers() -> dict:
    suppliers = _load_suppliers()
    return {"suppliers": list(suppliers.values()), "total": len(suppliers)}


@app.get("/scoring/health")
async def health() -> dict:
    return {"status": "healthy", "service": "scoring-service"}


@app.get("/scoring/ready")
async def ready() -> dict:
    return {"status": "ready"}
