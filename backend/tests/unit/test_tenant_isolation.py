"""Tenant isolation helper tests — one tenant must never reach another's data."""
from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from app.models.core import Company, Tenant
from app.security.tenant import (
    assert_company_in_tenant,
    resolve_scope_company_ids,
    tenant_company_ids,
)


async def _make_tenant_with_company(db_session, name: str):
    tenant = Tenant(
        id=uuid.uuid4(), name=name, slug=f"{name}-{uuid.uuid4().hex[:6]}",
        is_active=True,
    )
    db_session.add(tenant)
    await db_session.flush()
    company = Company(
        id=uuid.uuid4(), tenant_id=tenant.id, legal_name=f"{name} LLC",
        acquisition_target=False,
    )
    db_session.add(company)
    await db_session.flush()
    return tenant, company


@pytest.mark.asyncio
async def test_tenant_company_ids_returns_only_own(db_session):
    t1, c1 = await _make_tenant_with_company(db_session, "Alpha")
    t2, c2 = await _make_tenant_with_company(db_session, "Beta")

    ids1 = await tenant_company_ids(db_session, t1.id)
    ids2 = await tenant_company_ids(db_session, t2.id)

    assert ids1 == [c1.id]
    assert ids2 == [c2.id]
    assert c2.id not in ids1


@pytest.mark.asyncio
async def test_assert_company_in_tenant_allows_own(db_session):
    t1, c1 = await _make_tenant_with_company(db_session, "Alpha")
    # Does not raise.
    await assert_company_in_tenant(db_session, c1.id, t1.id)


@pytest.mark.asyncio
async def test_assert_company_in_tenant_blocks_cross_tenant(db_session):
    t1, _ = await _make_tenant_with_company(db_session, "Alpha")
    _, c2 = await _make_tenant_with_company(db_session, "Beta")

    with pytest.raises(HTTPException) as exc:
        await assert_company_in_tenant(db_session, c2.id, t1.id)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_resolve_scope_rejects_foreign_company(db_session):
    t1, c1 = await _make_tenant_with_company(db_session, "Alpha")
    _, c2 = await _make_tenant_with_company(db_session, "Beta")

    # No explicit company -> all of the tenant's companies.
    assert await resolve_scope_company_ids(db_session, t1.id, None) == [c1.id]
    # Own company -> just that one.
    assert await resolve_scope_company_ids(db_session, t1.id, c1.id) == [c1.id]
    # Another tenant's company -> 404.
    with pytest.raises(HTTPException) as exc:
        await resolve_scope_company_ids(db_session, t1.id, c2.id)
    assert exc.value.status_code == 404
