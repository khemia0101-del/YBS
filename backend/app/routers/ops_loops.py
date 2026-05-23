"""Continuous ops loops — CRUD plus manual run-now."""
from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import assert_company_in_tenant, get_tenant_id, require_analyst
from app.models.ops_loop import OpsLoop, OpsLoopRun
from app.models.users import User
from app.schemas.ops_loop import (
    OpsLoopCreateRequest,
    OpsLoopResponse,
    OpsLoopRunResponse,
    OpsLoopUpdateRequest,
)
from app.services.ops_loops.runner import run_loop

router = APIRouter()


@router.post("", response_model=OpsLoopResponse)
async def create_loop(
    body: OpsLoopCreateRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user: User = Depends(require_analyst),
) -> OpsLoopResponse:
    await assert_company_in_tenant(db, body.company_id, tenant_id)
    loop = OpsLoop(
        id=uuid.uuid4(),
        company_id=body.company_id,
        name=body.name,
        focus=body.focus,
        prompt=body.prompt,
        schedule_cron=body.schedule_cron,
        is_active=body.is_active,
        config=body.config,
    )
    db.add(loop)
    await db.flush()
    return OpsLoopResponse.model_validate(loop)


@router.get("", response_model=list[OpsLoopResponse])
async def list_loops(
    company_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> list[OpsLoopResponse]:
    await assert_company_in_tenant(db, company_id, tenant_id)
    rows = (
        await db.execute(
            select(OpsLoop)
            .where(OpsLoop.company_id == company_id)
            .order_by(OpsLoop.created_at.desc())
        )
    ).scalars().all()
    return [OpsLoopResponse.model_validate(r) for r in rows]


async def _load_loop(
    db: AsyncSession, loop_id: UUID, tenant_id: UUID
) -> OpsLoop:
    loop = (
        await db.execute(select(OpsLoop).where(OpsLoop.id == loop_id))
    ).scalar_one_or_none()
    if loop is None:
        raise HTTPException(status_code=404, detail="Loop not found")
    await assert_company_in_tenant(db, loop.company_id, tenant_id)
    return loop


@router.patch("/{loop_id}", response_model=OpsLoopResponse)
async def update_loop(
    loop_id: UUID,
    body: OpsLoopUpdateRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user: User = Depends(require_analyst),
) -> OpsLoopResponse:
    loop = await _load_loop(db, loop_id, tenant_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(loop, field, value)
    await db.flush()
    return OpsLoopResponse.model_validate(loop)


@router.post("/{loop_id}/run", response_model=OpsLoopRunResponse)
async def run_now(
    loop_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user: User = Depends(require_analyst),
) -> OpsLoopRunResponse:
    """Manually trigger one iteration of a loop right now."""
    loop = await _load_loop(db, loop_id, tenant_id)
    result = await run_loop(db, loop.id)
    return OpsLoopRunResponse.model_validate(result)


@router.get("/{loop_id}/runs", response_model=list[OpsLoopRunResponse])
async def list_runs(
    loop_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> list[OpsLoopRunResponse]:
    await _load_loop(db, loop_id, tenant_id)
    rows = (
        await db.execute(
            select(OpsLoopRun)
            .where(OpsLoopRun.loop_id == loop_id)
            .order_by(OpsLoopRun.started_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [OpsLoopRunResponse.model_validate(r) for r in rows]
