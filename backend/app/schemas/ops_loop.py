from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OpsLoopResponse(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    focus: str
    prompt: str
    schedule_cron: str
    is_active: bool
    config: dict | None
    last_run_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OpsLoopCreateRequest(BaseModel):
    company_id: UUID
    name: str
    focus: str = "metrics"
    prompt: str
    schedule_cron: str = "0 9 * * 1"
    config: dict | None = None
    is_active: bool = True


class OpsLoopUpdateRequest(BaseModel):
    name: str | None = None
    focus: str | None = None
    prompt: str | None = None
    schedule_cron: str | None = None
    config: dict | None = None
    is_active: bool | None = None


class OpsLoopRunResponse(BaseModel):
    id: UUID
    loop_id: UUID
    started_at: datetime
    ended_at: datetime | None
    status: str
    findings_summary: str | None
    proposed_actions_count: int
    error: str | None

    model_config = ConfigDict(from_attributes=True)
