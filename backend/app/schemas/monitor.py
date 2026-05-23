from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ObservationResponse(BaseModel):
    id: UUID
    company_id: UUID | None
    source_type: str
    source_ref: str
    title: str
    severity: str
    status: str
    content: dict | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiagnosisResponse(BaseModel):
    id: UUID
    observation_id: UUID
    root_cause_summary: str | None
    proposed_fix: str | None
    files_changed: list | None
    confidence: str
    reviewer_agent_verdict: dict | None
    status: str
    pr_url: str | None
    pr_description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RunMonitorResponse(BaseModel):
    observations_collected: dict[str, int]
    diagnoses_drafted: int


class ApproveDiagnosisResponse(BaseModel):
    diagnosis: DiagnosisResponse
    github: dict
