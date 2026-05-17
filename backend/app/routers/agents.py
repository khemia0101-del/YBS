from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import (
    assert_company_in_tenant,
    get_tenant_id,
    require_analyst,
    resolve_scope_company_ids,
)
from app.models.agent import AgentActionLog, AgentTask
from app.models.users import User
from app.schemas.agents import AgentActionLogResponse, AgentTaskResponse
from app.schemas.common import PaginatedResponse

router = APIRouter()


async def _load_task_in_tenant(
    db: AsyncSession, task_id: UUID, tenant_id: UUID
) -> AgentTask:
    result = await db.execute(select(AgentTask).where(AgentTask.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    await assert_company_in_tenant(db, task.company_id, tenant_id)
    return task


@router.get("/tasks", response_model=PaginatedResponse[AgentTaskResponse])
async def list_tasks(
    company_id: UUID | None = Query(None),
    status: str | None = Query(None),
    agent_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> PaginatedResponse[AgentTaskResponse]:
    allowed = await resolve_scope_company_ids(db, tenant_id, company_id)
    q = select(AgentTask).where(AgentTask.company_id.in_(allowed))
    if status:
        q = q.where(AgentTask.status == status)
    if agent_id:
        q = q.where(AgentTask.agent_id == agent_id)

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar() or 0

    q = q.order_by(AgentTask.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    tasks = result.scalars().all()

    return PaginatedResponse(
        items=[AgentTaskResponse.model_validate(t) for t in tasks],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/tasks/{task_id}", response_model=AgentTaskResponse)
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> AgentTaskResponse:
    task = await _load_task_in_tenant(db, task_id, tenant_id)
    return AgentTaskResponse.model_validate(task)


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: User = Depends(require_analyst),
) -> dict:
    task = await _load_task_in_tenant(db, task_id, tenant_id)
    if task.status not in ("queued", "awaiting_approval"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel task with status '{task.status}'",
        )
    task.status = "rejected"
    return {"task_id": str(task_id), "status": "cancelled"}


@router.get("/tasks/{task_id}/log", response_model=list[AgentActionLogResponse])
async def get_task_log(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> list[AgentActionLogResponse]:
    await _load_task_in_tenant(db, task_id, tenant_id)
    result = await db.execute(
        select(AgentActionLog)
        .where(AgentActionLog.task_id == task_id)
        .order_by(AgentActionLog.created_at)
    )
    logs = result.scalars().all()
    return [AgentActionLogResponse.model_validate(l) for l in logs]


@router.get("/action-logs", response_model=PaginatedResponse[AgentActionLogResponse])
async def list_action_logs(
    task_id: UUID | None = Query(None),
    agent_id: str | None = Query(None),
    action_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> PaginatedResponse[AgentActionLogResponse]:
    allowed = await resolve_scope_company_ids(db, tenant_id, None)
    q = (
        select(AgentActionLog)
        .join(AgentTask, AgentActionLog.task_id == AgentTask.id)
        .where(AgentTask.company_id.in_(allowed))
    )
    if task_id:
        q = q.where(AgentActionLog.task_id == task_id)
    if agent_id:
        q = q.where(AgentActionLog.agent_id == agent_id)
    if action_type:
        q = q.where(AgentActionLog.action_type == action_type)

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar() or 0

    q = q.order_by(AgentActionLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    logs = result.scalars().all()

    return PaginatedResponse(
        items=[AgentActionLogResponse.model_validate(l) for l in logs],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
    )
