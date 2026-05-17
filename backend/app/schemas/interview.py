from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class InterviewSessionCreate(BaseModel):
    role: str = "owner"  # owner | employee
    interviewee_name: str | None = None
    interviewee_email: str | None = None
    purpose: str = "operations"  # operations | onboarding


class MessageResponse(BaseModel):
    seq: int
    sender: str
    content: str

    model_config = ConfigDict(from_attributes=True)


class InterviewSessionResponse(BaseModel):
    id: UUID
    company_id: UUID
    role: str
    interviewee_name: str | None
    interviewee_email: str | None
    purpose: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnswerRequest(BaseModel):
    answer: str


class InsightResponse(BaseModel):
    id: UUID
    insight_type: str
    title: str
    content: dict | None

    model_config = ConfigDict(from_attributes=True)
