"""Core workflow engine with step execution, retries, and event emission."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Callable, Awaitable

import structlog

logger = structlog.get_logger(__name__)


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Step:
    name: str
    handler: Callable[..., Awaitable[dict]]
    retry_count: int = 3
    timeout_seconds: int = 30


@dataclass
class Workflow:
    name: str
    steps: list[Step]
    description: str = ""


@dataclass
class WorkflowRun:
    run_id: str
    workflow_name: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step: int = 0
    context: dict[str, Any] = field(default_factory=dict)
    history: list[dict] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""
    error: str = ""


class WorkflowEngine:
    def __init__(self) -> None:
        self._workflows: dict[str, Workflow] = {}
        self._runs: dict[str, WorkflowRun] = {}
        self._event_handlers: dict[str, list[Callable]] = {}

    def register_workflow(self, workflow: Workflow) -> None:
        self._workflows[workflow.name] = workflow
        logger.info("workflow.registered", name=workflow.name, steps=len(workflow.steps))

    async def start_workflow(self, workflow_name: str, context: dict) -> str:
        workflow = self._workflows.get(workflow_name)
        if not workflow:
            raise ValueError(f"Workflow '{workflow_name}' not found")

        run_id = f"wfr_{uuid.uuid4().hex[:12]}"
        run = WorkflowRun(
            run_id=run_id,
            workflow_name=workflow_name,
            status=WorkflowStatus.RUNNING,
            context=context,
            started_at=datetime.now(UTC).isoformat(),
        )
        self._runs[run_id] = run

        logger.info("workflow.started", run_id=run_id, workflow=workflow_name)
        await self._emit_event("workflow_started", {"run_id": run_id, "workflow": workflow_name})

        # Execute steps sequentially
        for i, step in enumerate(workflow.steps):
            run.current_step = i
            try:
                result = await self._execute_step(step, run.context)
                run.context.update(result)
                run.history.append({
                    "step": step.name,
                    "status": "completed",
                    "timestamp": datetime.now(UTC).isoformat(),
                })
                await self._emit_event("step_completed", {"run_id": run_id, "step": step.name})
            except Exception as exc:
                run.status = WorkflowStatus.FAILED
                run.error = str(exc)
                run.history.append({
                    "step": step.name,
                    "status": "failed",
                    "error": str(exc),
                    "timestamp": datetime.now(UTC).isoformat(),
                })
                logger.error("workflow.step_failed", run_id=run_id, step=step.name, error=str(exc))
                await self._emit_event("workflow_failed", {"run_id": run_id, "error": str(exc)})
                return run_id

        run.status = WorkflowStatus.COMPLETED
        run.completed_at = datetime.now(UTC).isoformat()
        await self._emit_event("workflow_completed", {"run_id": run_id})
        logger.info("workflow.completed", run_id=run_id)
        return run_id

    async def _execute_step(self, step: Step, context: dict) -> dict:
        for attempt in range(step.retry_count):
            try:
                return await step.handler(context)
            except Exception:
                if attempt == step.retry_count - 1:
                    raise
                logger.warning("workflow.step_retry", step=step.name, attempt=attempt + 1)
        return {}

    def get_run(self, run_id: str) -> WorkflowRun | None:
        return self._runs.get(run_id)

    def list_runs(self) -> list[dict]:
        return [
            {"run_id": r.run_id, "workflow": r.workflow_name, "status": r.status.value}
            for r in self._runs.values()
        ]

    def on_event(self, event_type: str, handler: Callable) -> None:
        self._event_handlers.setdefault(event_type, []).append(handler)

    async def _emit_event(self, event_type: str, payload: dict) -> None:
        for handler in self._event_handlers.get(event_type, []):
            try:
                await handler(payload)
            except Exception as exc:
                logger.error("workflow.event_handler_error", event=event_type, error=str(exc))
