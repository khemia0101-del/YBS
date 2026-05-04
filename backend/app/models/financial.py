from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.core import Company, Contract, Customer


class LaborBurdenAssumption(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "labor_burden_assumptions"

    company_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True
    )
    version: Mapped[str] = mapped_column(Text, nullable=False)
    fica_employer_pct: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    futa_pct: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    suta_pct: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    workers_comp_pct: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    benefits_pct: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    training_pct: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    total_burden_pct: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)


class ProfitabilityRun(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "profitability_runs"

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    calculation_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    approved_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_revenue: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    direct_labor: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    burden_cost: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    subcontractor_cost: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    supplies_cost: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    gross_profit: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    gross_margin_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 6), nullable=True)
    evidence_bundle: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    lines: Mapped[list[ProfitabilityRunLine]] = relationship(
        "ProfitabilityRunLine", back_populates="run"
    )


class ProfitabilityRunLine(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "profitability_run_lines"

    run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("profitability_runs.id"), nullable=False
    )
    contract_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False
    )
    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    revenue: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    direct_labor_cost: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    burden_cost: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    subcontractor_cost: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    supplies_cost: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    contribution_margin: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    contribution_margin_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 6), nullable=True)
    labor_hours: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    evidence_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    calculation_version: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    run: Mapped[ProfitabilityRun] = relationship("ProfitabilityRun", back_populates="lines")
    contract: Mapped[Contract] = relationship("Contract")
    customer: Mapped[Customer] = relationship("Customer")


class DSOSnapshot(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "dso_snapshots"

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    dso_days: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    total_ar: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    avg_daily_revenue: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    aging_0_30: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    aging_31_60: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    aging_61_90: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    aging_91_plus: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    evidence_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    calculation_version: Mapped[str | None] = mapped_column(Text, nullable=True)


class CashForecastRun(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "cash_forecast_runs"

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    forecast_start: Mapped[date] = mapped_column(Date, nullable=False)
    forecast_weeks: Mapped[int] = mapped_column(Integer, nullable=False, default=13)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="baseline")
    beginning_cash: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    ending_cash: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    min_cash_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    min_cash_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payroll_covered_through: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    approved_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Relationships
    weeks: Mapped[list[CashForecastWeek]] = relationship(
        "CashForecastWeek", back_populates="run"
    )


class CashForecastWeek(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "cash_forecast_weeks"

    run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cash_forecast_runs.id"), nullable=False
    )
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    beginning_cash: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    ar_collections: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    other_inflows: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    payroll_outflow: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    subcontractor_outflow: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    overhead_outflow: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    other_outflows: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    net_cash_flow: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    ending_cash: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    run: Mapped[CashForecastRun] = relationship("CashForecastRun", back_populates="weeks")


class StressTestRun(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "stress_test_runs"

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    base_forecast_run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cash_forecast_runs.id"), nullable=True
    )
    scenario_name: Mapped[str] = mapped_column(Text, nullable=False)
    scenario_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")


class Decision(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "decisions"

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    subject_type: Mapped[str] = mapped_column(String(30), nullable=False)
    subject_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    decision_type: Mapped[str] = mapped_column(String(30), nullable=False)
    label: Mapped[str] = mapped_column(String(30), nullable=False, default="APPROVAL_REQUIRED")
    rationale: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    approved_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    executed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    calculation_version: Mapped[str | None] = mapped_column(Text, nullable=True)


class ManualOverride(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "manual_overrides"

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    table_name: Mapped[str] = mapped_column(Text, nullable=False)
    record_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    field_name: Mapped[str] = mapped_column(Text, nullable=False)
    original_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    override_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    override_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PredictionTracking(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "prediction_tracking"

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    prediction_type: Mapped[str] = mapped_column(Text, nullable=False)
    subject_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    predicted_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    actual_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    prediction_date: Mapped[date] = mapped_column(Date, nullable=False)
    resolution_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    accuracy_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    calculation_version: Mapped[str | None] = mapped_column(Text, nullable=True)
