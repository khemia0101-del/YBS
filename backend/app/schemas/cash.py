from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ForecastRunResponse(BaseModel):
    id: UUID
    company_id: UUID
    run_date: date
    forecast_start: date
    forecast_weeks: int
    mode: str
    beginning_cash: Decimal | None
    ending_cash: Decimal | None
    min_cash_amount: Decimal | None
    min_cash_week: int | None
    payroll_covered_through: date | None
    status: str
    approved_by: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ForecastWeekResponse(BaseModel):
    id: UUID
    run_id: UUID
    week_number: int
    week_start: date
    beginning_cash: Decimal | None
    ar_collections: Decimal | None
    other_inflows: Decimal | None
    payroll_outflow: Decimal | None
    subcontractor_outflow: Decimal | None
    overhead_outflow: Decimal | None
    other_outflows: Decimal | None
    net_cash_flow: Decimal | None
    ending_cash: Decimal | None
    notes: str | None

    model_config = ConfigDict(from_attributes=True)


class StressTestRequest(BaseModel):
    company_id: UUID
    base_forecast_run_id: UUID | None = None
    scenario_name: str
    revenue_reduction_pct: Decimal = Decimal("0.20")
    ar_delay_days: int = 15
    payroll_increase_pct: Decimal = Decimal("0.05")
    beginning_cash: Decimal | None = None


class StressTestResponse(BaseModel):
    id: UUID
    company_id: UUID
    scenario_name: str
    scenario_params: dict | None
    results: dict | None
    run_date: date
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
