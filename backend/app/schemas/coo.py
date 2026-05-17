from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ConversationResponse(BaseModel):
    id: UUID
    company_id: UUID
    title: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CooMessageResponse(BaseModel):
    seq: int
    role: str
    content: str

    model_config = ConfigDict(from_attributes=True)


class CooActionResponse(BaseModel):
    id: UUID
    company_id: UUID
    conversation_id: UUID | None
    action_type: str
    title: str
    payload: dict
    status: str
    result: dict | None

    model_config = ConfigDict(from_attributes=True)


class SendMessageRequest(BaseModel):
    message: str


class EmployeeTaskResponse(BaseModel):
    id: UUID
    company_id: UUID
    title: str
    description: str | None
    assignee_name: str | None
    assignee_email: str | None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
