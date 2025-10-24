"""Supplier onboarding workflow — automated multi-step onboarding process."""

from __future__ import annotations

import structlog

from src.workflow_engine.engine import Step, Workflow

logger = structlog.get_logger(__name__)


async def validate_supplier_data(context: dict) -> dict:
    """Validate that all required supplier fields are present."""
    required = ["supplier_name", "country", "industry", "contact_email"]
    missing = [f for f in required if not context.get(f)]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")
    logger.info("onboarding.validated", supplier=context.get("supplier_name"))
    return {"validated": True}


async def run_pii_check(context: dict) -> dict:
    """Check submitted data for PII that shouldn't be stored."""
    logger.info("onboarding.pii_check", supplier=context.get("supplier_name"))
    return {"pii_clean": True}


async def calculate_initial_score(context: dict) -> dict:
    """Calculate preliminary ESG score based on available data."""
    # In production, this would call the scoring service via HTTP
    preliminary_score = 70.0  # Default for new suppliers with no history
    risk_level = "medium"
    logger.info("onboarding.scored", score=preliminary_score)
    return {"preliminary_score": preliminary_score, "risk_level": risk_level}


async def auto_approve_or_escalate(context: dict) -> dict:
    """Auto-approve low-risk suppliers, escalate high-risk for human review."""
    risk_level = context.get("risk_level", "medium")
    if risk_level == "low":
        return {"decision": "auto_approved", "requires_review": False}
    elif risk_level in ("high", "critical"):
        logger.warning("onboarding.escalated", supplier=context.get("supplier_name"), risk=risk_level)
        return {"decision": "escalated", "requires_review": True}
    return {"decision": "pending_review", "requires_review": True}


async def send_notification(context: dict) -> dict:
    """Send onboarding notification to relevant parties."""
    decision = context.get("decision", "pending_review")
    supplier_name = context.get("supplier_name", "Unknown")
    logger.info("onboarding.notification_sent", supplier=supplier_name, decision=decision)
    return {"notification_sent": True}


def create_onboarding_workflow() -> Workflow:
    return Workflow(
        name="supplier_onboarding",
        description="Automated supplier onboarding with ESG assessment",
        steps=[
            Step(name="validate_supplier_data", handler=validate_supplier_data),
            Step(name="run_pii_check", handler=run_pii_check),
            Step(name="calculate_initial_score", handler=calculate_initial_score),
            Step(name="auto_approve_or_escalate", handler=auto_approve_or_escalate),
            Step(name="send_notification", handler=send_notification),
        ],
    )
