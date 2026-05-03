from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AgentTaskResponse(BaseModel):
    id: UUID
    company_id: UUID
    task_type: str
    subject_type: str | None
    subject_id: UUID | None
    priority: int
    status: str
    agent_id: str
    input_params: dict | None
    output_data: dict | None
    error_message: str | None
    retry_count: int
    max_retries: int
    scheduled_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    parent_task_id: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentActionLogResponse(BaseModel):
    id: UUID
    task_id: UUID
    agent_id: str
    action_type: str
    description: str | None
    input_snapshot: dict | None
    output_snapshot: dict | None
    tables_read: list[str] | None
    tables_written: list[str] | None
    was_approved: bool | None
    approved_by: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApprovalRequestResponse(BaseModel):
    id: UUID
    company_id: UUID
    task_id: UUID | None
    decision_id: UUID | None
    requested_by: str
    subject_description: str | None
    action_description: str | None
    risk_level: str
    required_role: str
    status: str
    reviewed_by: UUID | None
    reviewed_at: datetime | None
    review_notes: str | None
    expires_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApproveActionRequest(BaseModel):
    notes: str | None = None
