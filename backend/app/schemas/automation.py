from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AutomationItemResponse(BaseModel):
    id: UUID
    company_id: UUID
    title: str
    description: str | None
    category: str | None
    source: str
    source_ref: str | None
    impact: str
    effort: str
    priority_score: int
    status: str
    agent_task_id: UUID | None

    model_config = ConfigDict(from_attributes=True)
