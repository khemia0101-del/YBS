"""Employee-facing in-app task list."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import assert_company_in_tenant, get_tenant_id
from app.models.coo import EmployeeTask
from app.schemas.coo import EmployeeTaskResponse

router = APIRouter()


@router.get("", response_model=list[EmployeeTaskResponse])
async def list_employee_tasks(
    company_id: UUID = Query(...),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> list[EmployeeTaskResponse]:
    await assert_company_in_tenant(db, company_id, tenant_id)
    q = select(EmployeeTask).where(EmployeeTask.company_id == company_id)
    if status:
        q = q.where(EmployeeTask.status == status)
    result = await db.execute(q.order_by(EmployeeTask.created_at.desc()))
    return [EmployeeTaskResponse.model_validate(t) for t in result.scalars().all()]


@router.post("/{task_id}/complete", response_model=EmployeeTaskResponse)
async def complete_employee_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> EmployeeTaskResponse:
    result = await db.execute(select(EmployeeTask).where(EmployeeTask.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    await assert_company_in_tenant(db, task.company_id, tenant_id)
    task.status = "done"
    await db.flush()
    return EmployeeTaskResponse.model_validate(task)
