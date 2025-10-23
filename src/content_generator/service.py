"""Content Generator FastAPI service."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import structlog
from fastapi import FastAPI, HTTPException
from openai import AsyncAzureOpenAI
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.content_generator.generators.email_generator import EmailGenerator
from src.content_generator.generators.report_generator import SustainabilityReportGenerator

logger = structlog.get_logger(__name__)
app = FastAPI(title="EcoSupplyAI Content Generator", version="0.1.0")

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "sample" / "suppliers.json"
_reports_store: dict[str, dict] = {}


class ContentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    AZURE_OPENAI_ENDPOINT: str = "https://example.openai.azure.com/"
    AZURE_OPENAI_API_KEY: str = "change-me"
    AZURE_OPENAI_DEPLOYMENT_NAME: str = "gpt-4o"
    AZURE_OPENAI_API_VERSION: str = "2024-12-01-preview"


class ReportRequest(BaseModel):
    supplier_ids: list[str] = Field(..., examples=[["SUP-001", "SUP-002"]])
    report_type: str = Field(default="quarterly")
    period: str = Field(default="Q4-2025")


class EmailRequest(BaseModel):
    supplier_id: str
    email_type: str = Field(default="onboarding", examples=["onboarding", "audit"])
    findings: list[str] = Field(default_factory=list)


def _get_client() -> AsyncAzureOpenAI:
    settings = ContentSettings()
    return AsyncAzureOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
    )


def _load_suppliers() -> dict[str, dict]:
    if DATA_PATH.exists():
        return {s["id"]: s for s in json.loads(DATA_PATH.read_text()).get("suppliers", [])}
    return {}


@app.post("/content/report")
async def generate_report(request: ReportRequest) -> dict:
    suppliers_db = _load_suppliers()
    suppliers = [suppliers_db[sid] for sid in request.supplier_ids if sid in suppliers_db]
    if not suppliers:
        raise HTTPException(status_code=404, detail="No matching suppliers found")

    # Simple scoring for report
    from src.scoring_service.models.esg_scorer import ESGScorer
    scorer = ESGScorer()
    scores = [scorer.score_supplier(s) for s in suppliers]

    client = _get_client()
    generator = SustainabilityReportGenerator(client)
    result = await generator.generate_quarterly_report(suppliers, scores, request.period)

    report_id = f"rpt_{uuid.uuid4().hex[:8]}"
    _reports_store[report_id] = result
    result["report_id"] = report_id
    return result


@app.get("/content/reports/{report_id}")
async def get_report(report_id: str) -> dict:
    report = _reports_store.get(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.post("/content/email")
async def generate_email(request: EmailRequest) -> dict:
    suppliers = _load_suppliers()
    supplier = suppliers.get(request.supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier {request.supplier_id} not found")

    client = _get_client()
    generator = EmailGenerator(client)

    if request.email_type == "audit":
        draft = await generator.generate_audit_request(supplier, request.findings)
    else:
        draft = await generator.generate_onboarding_email(supplier)

    return draft.model_dump()


@app.get("/content/health")
async def health() -> dict:
    return {"status": "healthy", "service": "content-generator"}


@app.get("/content/ready")
async def ready() -> dict:
    return {"status": "ready"}
