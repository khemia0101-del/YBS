from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class QoERunResponse(BaseModel):
    id: UUID
    company_id: UUID
    run_date: date
    analysis_period_start: date
    analysis_period_end: date
    reported_ebitda: Decimal | None
    adjusted_ebitda: Decimal | None
    total_addbacks: Decimal | None
    total_negative_adj: Decimal | None
    normalized_ebitda: Decimal | None
    ebitda_margin_pct: Decimal | None
    revenue_concentration_flag: bool
    customer_count: int | None
    calculation_version: str | None
    status: str
    approved_by: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ESOPAdjustmentResponse(BaseModel):
    id: UUID
    qoe_run_id: UUID
    adj_type: str
    category: str | None
    description: str | None
    amount: Decimal | None
    period: str | None
    evidence_id: UUID | None
    evidence_description: str | None
    confidence_score: Decimal | None
    requires_approval: bool
    approved_by: UUID | None
    approved_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ValuationPackageResponse(BaseModel):
    qoe_run_id: UUID
    download_url: str
    expires_at: datetime
    files: list[dict]
