"""Automation roadmap — build the backlog and dispatch items to the agent queue."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import assert_company_in_tenant, get_tenant_id, require_analyst
from app.models.automation import AutomationItem
from app.models.users import User
from app.schemas.automation import AutomationItemResponse
from app.services.agents.task_queue import enqueue_task, request_approval
from app.services.automation.roadmap import build_roadmap

router = APIRouter()


@router.post("/roadmap/build", response_model=list[AutomationItemResponse])
async def build(
    company_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user: User = Depends(require_analyst),
) -> list[AutomationItemResponse]:
    """Refresh the automation backlog from interview insights + observed signals."""
    await assert_company_in_tenant(db, company_id, tenant_id)
    items = await build_roadmap(db, company_id)
    return [AutomationItemResponse.model_validate(i) for i in items]


@router.get("/items", response_model=list[AutomationItemResponse])
async def list_items(
    company_id: UUID = Query(...),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> list[AutomationItemResponse]:
    await assert_company_in_tenant(db, company_id, tenant_id)
    q = select(AutomationItem).where(AutomationItem.company_id == company_id)
    if status:
        q = q.where(AutomationItem.status == status)
    result = await db.execute(
        q.order_by(AutomationItem.priority_score.desc(), AutomationItem.title)
    )
    return [AutomationItemResponse.model_validate(i) for i in result.scalars().all()]


@router.post("/items/{item_id}/dispatch")
async def dispatch_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user: User = Depends(require_analyst),
) -> dict:
    """Queue an automation item as an AgentTask and route it through approval."""
    result = await db.execute(
        select(AutomationItem).where(AutomationItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Automation item not found")
    await assert_company_in_tenant(db, item.company_id, tenant_id)
    if item.status != "proposed":
        raise HTTPException(
            status_code=409, detail=f"Item is already '{item.status}'"
        )

    task_id = await enqueue_task(
        db,
        task_type="automation_item",
        company_id=item.company_id,
        input_params={"automation_item_id": str(item.id), "title": item.title},
        subject_type="automation_item",
        subject_id=item.id,
    )
    await request_approval(
        db,
        task_id=task_id,
        company_id=item.company_id,
        subject_description=item.title,
        action_description=item.description or item.title,
        risk_level="medium",
        required_role="analyst",
    )
    item.status = "dispatched"
    item.agent_task_id = task_id
    await db.flush()
    return {
        "item_id": str(item.id),
        "status": "dispatched",
        "agent_task_id": str(task_id),
    }
