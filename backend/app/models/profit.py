"""
Profitability recommendations.

A ProfitRecommendation is one ranked, dollar-quantified idea for making a
business more profitable. Recommendations are generated from QoE output, KPI
snapshots, and interview insights, and tracked over time.
"""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class ProfitRecommendation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "profit_recommendations"
    __table_args__ = (
        UniqueConstraint("company_id", "title", name="uq_profit_rec_company_title"),
    )

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # pricing | cost_reduction | margin | churn | upsell | revenue_mix
    category: Mapped[str] = mapped_column(String(30), nullable=False, default="margin")
    estimated_annual_impact: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    effort: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    confidence: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    # proposed | accepted | dismissed | done
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="proposed")
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="rules")
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
