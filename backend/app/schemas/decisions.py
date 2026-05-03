from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DecisionResponse(BaseModel):
    id: UUID
    company_id: UUID
    subject_type: str
    subject_id: UUID | None
    decision_type: str
    label: str
    rationale: dict | None
    recommended_action: str | None
    recommended_price: Decimal | None
    status: str
    approved_by: UUID | None
    approved_at: datetime | None
    executed_at: datetime | None
    calculation_version: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BidScoreRequest(BaseModel):
    company_id: UUID
    customer_name: str
    site_address: dict
    square_footage: Decimal
    service_frequency: str
    contract_type: str = "fixed"
    proposed_monthly_value: Decimal
    estimated_hours_per_month: Decimal
    hourly_rate: Decimal
    subcontractor_pct: Decimal = Decimal("0")
    overhead_allocation_pct: Decimal = Decimal("0.15")


class BidScoreResponse(BaseModel):
    decision_type: str
    label: str
    recommended_price: Decimal
    contribution_margin: Decimal
    contribution_margin_pct: Decimal
    rationale: dict
    recommended_action: str
