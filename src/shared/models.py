"""SQLAlchemy ORM models for EcoSupplyAI persistent data."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.database import Base


# ---------------------------------------------------------------------------
# Supplier
# ---------------------------------------------------------------------------
class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    external_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(128))
    industry: Mapped[str] = mapped_column(String(128))
    tier: Mapped[int] = mapped_column(Integer, default=1)
    contact_email: Mapped[str | None] = mapped_column(String(255))
    annual_revenue_eur: Mapped[float | None] = mapped_column(Float)
    employee_count: Mapped[int | None] = mapped_column(Integer)
    certifications: Mapped[list | None] = mapped_column(ARRAY(String), default=list)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    scores: Mapped[list[ESGScore]] = relationship(back_populates="supplier")
    audit_logs: Mapped[list[AuditLog]] = relationship(back_populates="supplier")


# ---------------------------------------------------------------------------
# ESG Score
# ---------------------------------------------------------------------------
class ESGScore(Base):
    __tablename__ = "esg_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id"), index=True
    )
    composite_score: Mapped[float] = mapped_column(Float, nullable=False)
    environmental_score: Mapped[float] = mapped_column(Float)
    social_score: Mapped[float] = mapped_column(Float)
    governance_score: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(32))
    breakdown: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    contributing_factors: Mapped[list | None] = mapped_column(JSONB, default=list)
    scored_by: Mapped[str | None] = mapped_column(String(64))
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    supplier: Mapped[Supplier] = relationship(back_populates="scores")


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    actor: Mapped[str] = mapped_column(String(128))
    details: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    supplier: Mapped[Supplier | None] = relationship(back_populates="audit_logs")


# ---------------------------------------------------------------------------
# Emission Record (for forecasting)
# ---------------------------------------------------------------------------
class EmissionRecord(Base):
    __tablename__ = "emission_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id"), index=True
    )
    scope: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, or 3
    period: Mapped[str] = mapped_column(String(32))  # e.g. "2025-Q1"
    emissions_tons: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str | None] = mapped_column(String(128))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ---------------------------------------------------------------------------
# Chat Session
# ---------------------------------------------------------------------------
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str | None] = mapped_column(String(512))
    messages: Mapped[list | None] = mapped_column(JSONB, default=list)
    token_usage: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# Generated Report
# ---------------------------------------------------------------------------
class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    report_type: Mapped[str] = mapped_column(String(64))
    period: Mapped[str] = mapped_column(String(32))
    supplier_ids: Mapped[list | None] = mapped_column(ARRAY(String))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    content: Mapped[dict | None] = mapped_column(JSONB)
    generated_by: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
