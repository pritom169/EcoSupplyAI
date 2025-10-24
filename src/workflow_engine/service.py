"""Workflow Engine FastAPI service."""

from __future__ import annotations

import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.workflow_engine.engine import WorkflowEngine
from src.workflow_engine.workflows.onboarding import create_onboarding_workflow

logger = structlog.get_logger(__name__)
app = FastAPI(title="EcoSupplyAI Workflow Engine", version="0.1.0")

# Initialize engine and register workflows
engine = WorkflowEngine()
engine.register_workflow(create_onboarding_workflow())


class StartWorkflowRequest(BaseModel):
    context: dict = {}


@app.post("/workflows/start/{workflow_name}")
async def start_workflow(workflow_name: str, request: StartWorkflowRequest | None = None) -> dict:
    context = request.context if request else {}
    # Also accept flat body as context
    if not context and request:
        context = request.model_dump().get("context", {})
    try:
        run_id = await engine.start_workflow(workflow_name, context)
        run = engine.get_run(run_id)
        return {
            "run_id": run_id,
            "status": run.status.value if run else "unknown",
            "workflow": workflow_name,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/workflows/status/{run_id}")
async def get_workflow_status(run_id: str) -> dict:
    run = engine.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return {
        "run_id": run.run_id,
        "workflow": run.workflow_name,
        "status": run.status.value,
        "current_step": run.current_step,
        "history": run.history,
        "error": run.error,
    }


@app.get("/workflows/runs")
async def list_runs() -> dict:
    return {"runs": engine.list_runs()}


@app.get("/workflows/health")
async def health() -> dict:
    return {"status": "healthy", "service": "workflow-engine"}


@app.get("/workflows/ready")
async def ready() -> dict:
    return {"status": "ready"}
