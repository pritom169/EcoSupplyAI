"""Initial schema — suppliers, scores, audit logs, emissions, sessions, reports.

Revision ID: 001_initial
Revises: None
Create Date: 2025-01-01 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # -- Suppliers -----------------------------------------------------------
    op.create_table(
        "suppliers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("external_id", sa.String(64), unique=True, index=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("country", sa.String(128)),
        sa.Column("industry", sa.String(128)),
        sa.Column("tier", sa.Integer, default=1),
        sa.Column("contact_email", sa.String(255)),
        sa.Column("annual_revenue_eur", sa.Float),
        sa.Column("employee_count", sa.Integer),
        sa.Column("certifications", ARRAY(sa.String)),
        sa.Column("metadata", JSONB, default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # -- ESG Scores ----------------------------------------------------------
    op.create_table(
        "esg_scores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("supplier_id", UUID(as_uuid=True), sa.ForeignKey("suppliers.id"), index=True),
        sa.Column("composite_score", sa.Float, nullable=False),
        sa.Column("environmental_score", sa.Float),
        sa.Column("social_score", sa.Float),
        sa.Column("governance_score", sa.Float),
        sa.Column("risk_level", sa.String(32)),
        sa.Column("breakdown", JSONB),
        sa.Column("contributing_factors", JSONB),
        sa.Column("scored_by", sa.String(64)),
        sa.Column("scored_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # -- Audit Logs ----------------------------------------------------------
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("supplier_id", UUID(as_uuid=True), sa.ForeignKey("suppliers.id"), nullable=True, index=True),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("actor", sa.String(128)),
        sa.Column("details", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # -- Emission Records ----------------------------------------------------
    op.create_table(
        "emission_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("supplier_id", UUID(as_uuid=True), sa.ForeignKey("suppliers.id"), index=True),
        sa.Column("scope", sa.Integer, nullable=False),
        sa.Column("period", sa.String(32)),
        sa.Column("emissions_tons", sa.Float, nullable=False),
        sa.Column("source", sa.String(128)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # -- Chat Sessions -------------------------------------------------------
    op.create_table(
        "chat_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(128), index=True),
        sa.Column("title", sa.String(512)),
        sa.Column("messages", JSONB),
        sa.Column("token_usage", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # -- Generated Reports ---------------------------------------------------
    op.create_table(
        "generated_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("report_type", sa.String(64)),
        sa.Column("period", sa.String(32)),
        sa.Column("supplier_ids", ARRAY(sa.String)),
        sa.Column("status", sa.String(32), default="pending"),
        sa.Column("content", JSONB),
        sa.Column("generated_by", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("generated_reports")
    op.drop_table("chat_sessions")
    op.drop_table("emission_records")
    op.drop_table("audit_logs")
    op.drop_table("esg_scores")
    op.drop_table("suppliers")
