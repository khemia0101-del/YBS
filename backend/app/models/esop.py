from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.core import Company


class QoERun(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "qoe_runs"

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    analysis_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    analysis_period_end: Mapped[date] = mapped_column(Date, nullable=False)
    reported_ebitda: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    adjusted_ebitda: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    total_addbacks: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    total_negative_adj: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    normalized_ebitda: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    ebitda_margin_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 6), nullable=True)
    revenue_concentration_flag: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    customer_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calculation_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    approved_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    evidence_bundle: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    adjustments: Mapped[list[ESOPAdjustment]] = relationship(
        "ESOPAdjustment", back_populates="qoe_run"
    )
    evidence_files: Mapped[list[ValuationEvidenceFile]] = relationship(
        "ValuationEvidenceFile", back_populates="qoe_run"
    )


class ESOPAdjustment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "esop_adjustments"

    qoe_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("qoe_runs.id"), nullable=False
    )
    adj_type: Mapped[str] = mapped_column(String(30), nullable=False)
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    period: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    evidence_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    approved_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    qoe_run: Mapped[QoERun] = relationship("QoERun", back_populates="adjustments")


class ValuationEvidenceFile(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "valuation_evidence_files"

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    qoe_run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("qoe_runs.id"), nullable=True
    )
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    file_s3_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    period_covered: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Relationships
    qoe_run: Mapped[QoERun | None] = relationship(
        "QoERun", back_populates="evidence_files"
    )
