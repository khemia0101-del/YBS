from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TenantCreate(BaseModel):
    name: str
    slug: str
    admin_email: str
    admin_password: str
    admin_full_name: str | None = None


class TenantResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompanyCreate(BaseModel):
    legal_name: str
    dba_name: str | None = None
    ein: str | None = None
    founded_date: date | None = None
    acquisition_target: bool = False


class CompanyResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    legal_name: str
    dba_name: str | None
    ein: str | None
    founded_date: date | None
    acquisition_target: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenantUserCreate(BaseModel):
    email: str
    password: str
    full_name: str | None = None
    role: str = "viewer"
