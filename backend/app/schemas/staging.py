from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ExceptionResponse(BaseModel):
    id: UUID
    raw_record_id: UUID
    record_type: str
    extracted_data: dict | None
    confidence_score: Decimal | None
    confidence_reasons: list | None
    match_suggestions: list | None
    status: str
    reviewed_by: UUID | None
    reviewed_at: datetime | None
    review_notes: str | None
    auto_approved_at: datetime | None
    auto_approval_rule: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExceptionStats(BaseModel):
    total: int
    by_status: dict[str, int]
    by_record_type: dict[str, int]
    avg_confidence: float | None
    auto_approve_rate: float | None


class ApproveRequest(BaseModel):
    notes: str | None = None
    matched_entity_id: UUID | None = None


class BulkApproveRequest(BaseModel):
    ids: list[UUID]
    notes: str | None = None


class MatchRequest(BaseModel):
    entity_id: UUID
    entity_type: str
    notes: str | None = None
