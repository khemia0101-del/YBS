"""
Tenant, business (Company) and user onboarding.

Internal/admin-driven only — there is no public self-serve signup.
All company and user operations are scoped to the caller's tenant.
"""
from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_tenant_id, require_admin
from app.models.core import Company, Tenant
from app.models.users import User
from app.schemas.auth import UserResponse
from app.schemas.tenants import (
    CompanyCreate,
    CompanyResponse,
    TenantCreate,
    TenantResponse,
    TenantUserCreate,
)
from app.security.auth import get_current_active_user, hash_password

router = APIRouter()

VALID_ROLES = {"admin", "analyst", "operator", "viewer", "agent"}


@router.post("/", response_model=TenantResponse)
async def create_tenant(
    body: TenantCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> TenantResponse:
    """Provision a new tenant and its first admin user."""
    existing = await db.execute(select(Tenant).where(Tenant.slug == body.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Tenant slug already exists")

    email_taken = await db.execute(select(User).where(User.email == body.admin_email))
    if email_taken.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Admin email already exists")

    tenant = Tenant(id=uuid.uuid4(), name=body.name, slug=body.slug, is_active=True)
    db.add(tenant)
    await db.flush()

    admin = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=body.admin_email,
        hashed_password=hash_password(body.admin_password),
        full_name=body.admin_full_name,
        role="admin",
        is_active=True,
    )
    db.add(admin)
    await db.flush()
    return TenantResponse.model_validate(tenant)


@router.get("/me", response_model=TenantResponse)
async def get_my_tenant(
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> TenantResponse:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantResponse.model_validate(tenant)


@router.get("/companies", response_model=list[CompanyResponse])
async def list_companies(
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> list[CompanyResponse]:
    result = await db.execute(
        select(Company).where(Company.tenant_id == tenant_id).order_by(Company.legal_name)
    )
    return [CompanyResponse.model_validate(c) for c in result.scalars().all()]


@router.post("/companies", response_model=CompanyResponse)
async def create_company(
    body: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _admin: User = Depends(require_admin),
) -> CompanyResponse:
    """Add a business to the caller's tenant."""
    company = Company(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        legal_name=body.legal_name,
        dba_name=body.dba_name,
        ein=body.ein,
        founded_date=body.founded_date,
        acquisition_target=body.acquisition_target,
    )
    db.add(company)
    await db.flush()
    return CompanyResponse.model_validate(company)


@router.get("/users", response_model=list[UserResponse])
async def list_tenant_users(
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _admin: User = Depends(require_admin),
) -> list[UserResponse]:
    result = await db.execute(
        select(User).where(User.tenant_id == tenant_id).order_by(User.email)
    )
    return [UserResponse.model_validate(u) for u in result.scalars().all()]


@router.post("/users", response_model=UserResponse)
async def create_tenant_user(
    body: TenantUserCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _admin: User = Depends(require_admin),
) -> UserResponse:
    """Create a user inside the caller's tenant."""
    if body.role not in VALID_ROLES:
        raise HTTPException(
            status_code=400, detail=f"Invalid role. Must be one of: {sorted(VALID_ROLES)}"
        )
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already exists")

    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return UserResponse.model_validate(user)
