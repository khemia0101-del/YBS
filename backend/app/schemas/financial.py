from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProfitabilityRunResponse(BaseModel):
    id: UUID
    company_id: UUID
    run_date: date
    period_start: date
    period_end: date
    calculation_version: str | None
    status: str
    approved_by: UUID | None
    approved_at: datetime | None
    total_revenue: Decimal | None
    direct_labor: Decimal | None
    burden_cost: Decimal | None
    subcontractor_cost: Decimal | None
    gross_profit: Decimal | None
    gross_margin_pct: Decimal | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProfitabilityRunLineResponse(BaseModel):
    id: UUID
    run_id: UUID
    contract_id: UUID
    customer_id: UUID
    revenue: Decimal | None
    direct_labor_cost: Decimal | None
    burden_cost: Decimal | None
    subcontractor_cost: Decimal | None
    contribution_margin: Decimal | None
    contribution_margin_pct: Decimal | None
    labor_hours: Decimal | None
    confidence_score: Decimal | None
    calculation_version: str | None

    model_config = ConfigDict(from_attributes=True)


class DSOResponse(BaseModel):
    id: UUID
    company_id: UUID
    snapshot_date: date
    dso_days: Decimal | None
    total_ar: Decimal | None
    avg_daily_revenue: Decimal | None
    aging_0_30: Decimal | None
    aging_31_60: Decimal | None
    aging_61_90: Decimal | None
    aging_91_plus: Decimal | None
    calculation_version: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConcentrationResponse(BaseModel):
    customer_id: UUID
    customer_name: str
    revenue_total: Decimal
    concentration_pct: Decimal
    is_flagged: bool
    contract_count: int
