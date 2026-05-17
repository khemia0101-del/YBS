"""
Adaptive business profile.

Instead of hardcoding any vertical, each Company has a BusinessProfile plus a set of
MetricDefinitions. The metrics/automation/growth engines read this configuration so the
platform can describe any business from that business's own inputs.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class BusinessProfile(Base, UUIDMixin, TimestampMixin):
    """What a business is and how it should be measured — one row per Company."""

    __tablename__ = "business_profiles"
    __table_args__ = (
        UniqueConstraint("company_id", name="uq_business_profile_company"),
    )

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    industry: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    north_star_metric: Mapped[str | None] = mapped_column(Text, nullable=True)
    # {"metric_key": str, "current_value": num, "target_value": num, "deadline": "YYYY-MM-DD"}
    growth_goal: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    automation_candidates: Mapped[list | None] = mapped_column(JSON, nullable=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # "manual" | "ai_inferred"
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    is_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    metric_definitions: Mapped[list[MetricDefinition]] = relationship(
        "MetricDefinition", back_populates="profile"
    )


class MetricDefinition(Base, UUIDMixin, TimestampMixin):
    """A KPI a business tracks. Engines read these rather than hardcoding any vertical."""

    __tablename__ = "metric_definitions"
    __table_args__ = (
        UniqueConstraint("company_id", "key", name="uq_metric_def_company_key"),
    )

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    profile_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("business_profiles.id"), nullable=True
    )
    key: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "count" | "currency" | "percent" | "ratio" | "days"
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="count")
    # "growth" | "financial" | "operational"
    category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # "manual" | "formula" | "derived"
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    formula: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    is_north_star: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    profile: Mapped[BusinessProfile | None] = relationship(
        "BusinessProfile", back_populates="metric_definitions"
    )
    snapshots: Mapped[list[MetricSnapshot]] = relationship(
        "MetricSnapshot", back_populates="metric_definition"
    )


class MetricSnapshot(Base, UUIDMixin, TimestampMixin):
    """A point-in-time value of a metric, for trend tracking."""

    __tablename__ = "metric_snapshots"

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    metric_definition_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("metric_definitions.id"), nullable=False
    )
    period_date: Mapped[date] = mapped_column(Date, nullable=False)
    # "daily" | "weekly" | "monthly"
    period_type: Mapped[str] = mapped_column(String(20), nullable=False, default="monthly")
    value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    # "computed" | "manual" | "imported"
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="computed")

    metric_definition: Mapped[MetricDefinition] = relationship(
        "MetricDefinition", back_populates="snapshots"
    )
