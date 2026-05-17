"""
Tenant isolation helpers.

Every business record belongs (directly or via its Company) to a Tenant.
These utilities resolve the caller's tenant from the authenticated user and
let routers scope their queries so one tenant can never read another's data.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.core import Company
from app.models.users import User
from app.security.auth import get_current_active_user


async def get_tenant_id(
    current_user: User = Depends(get_current_active_user),
) -> UUID:
    """FastAPI dependency — the caller's tenant. 403 if the user has none."""
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not assigned to a tenant",
        )
    return current_user.tenant_id


async def tenant_company_ids(db: AsyncSession, tenant_id: UUID) -> list[UUID]:
    """All Company ids owned by a tenant."""
    result = await db.execute(
        select(Company.id).where(Company.tenant_id == tenant_id)
    )
    return [row[0] for row in result.all()]


async def assert_company_in_tenant(
    db: AsyncSession, company_id: UUID, tenant_id: UUID
) -> None:
    """Raise 404 unless the company belongs to the tenant."""
    result = await db.execute(
        select(Company.id).where(
            Company.id == company_id, Company.tenant_id == tenant_id
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Company not found")


async def resolve_scope_company_ids(
    db: AsyncSession, tenant_id: UUID, company_id: UUID | None
) -> list[UUID]:
    """
    Resolve the set of company ids a query should be limited to.

    - If ``company_id`` is given, validate it belongs to the tenant and
      return just that one.
    - Otherwise return every company owned by the tenant.
    """
    if company_id is not None:
        await assert_company_in_tenant(db, company_id, tenant_id)
        return [company_id]
    return await tenant_company_ids(db, tenant_id)
