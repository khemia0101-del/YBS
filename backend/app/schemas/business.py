from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BusinessProfileUpdate(BaseModel):
    industry: str | None = None
    business_model: str | None = None
    description: str | None = None
    north_star_metric: str | None = None
    growth_goal: dict | None = None
    automation_candidates: list | None = None
    config: dict | None = None
    is_confirmed: bool | None = None


class BusinessProfileResponse(BaseModel):
    id: UUID
    company_id: UUID
    industry: str | None
    business_model: str | None
    description: str | None
    north_star_metric: str | None
    growth_goal: dict | None
    automation_candidates: list | None
    config: dict | None
    source: str
    is_confirmed: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MetricDefinitionCreate(BaseModel):
    key: str
    name: str
    description: str | None = None
    unit: str = "count"
    category: str | None = None
    source: str = "manual"
    formula: str | None = None
    target_value: Decimal | None = None
    is_north_star: bool = False


class MetricDefinitionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    unit: str | None = None
    category: str | None = None
    formula: str | None = None
    target_value: Decimal | None = None
    is_north_star: bool | None = None
    is_active: bool | None = None


class MetricDefinitionResponse(BaseModel):
    id: UUID
    company_id: UUID
    key: str
    name: str
    description: str | None
    unit: str
    category: str | None
    source: str
    formula: str | None
    target_value: Decimal | None
    is_north_star: bool
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class MetricSnapshotCreate(BaseModel):
    period_date: date
    period_type: str = "monthly"
    value: Decimal
    source: str = "manual"


class MetricSnapshotResponse(BaseModel):
    id: UUID
    metric_definition_id: UUID
    period_date: date
    period_type: str
    value: Decimal
    source: str

    model_config = ConfigDict(from_attributes=True)
