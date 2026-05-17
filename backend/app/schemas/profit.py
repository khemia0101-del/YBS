from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProfitRecommendationResponse(BaseModel):
    id: UUID
    company_id: UUID
    title: str
    description: str | None
    category: str
    estimated_annual_impact: Decimal | None
    effort: str
    confidence: str
    status: str
    source: str
    rationale: str | None

    model_config = ConfigDict(from_attributes=True)
