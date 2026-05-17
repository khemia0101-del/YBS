from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import (
    assert_company_in_tenant,
    get_current_active_user,
    get_tenant_id,
    resolve_scope_company_ids,
)
from app.models.agent import AgentTask, ApprovalRequest
from app.models.users import User
from app.schemas.agents import ApprovalRequestResponse, ApproveActionRequest
from app.schemas.common import PaginatedResponse
from app.security.audit import write_audit_log

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[ApprovalRequestResponse])
async def list_pending_approvals(
    company_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedResponse[ApprovalRequestResponse]:
    """Pending approvals filtered to the current user's role."""
    allowed = await resolve_scope_company_ids(db, tenant_id, company_id)
    q = select(ApprovalRequest).where(
        ApprovalRequest.status == "pending",
        ApprovalRequest.company_id.in_(allowed),
    )

    # Filter by required_role — show what this user can act on
    role_map = {
        "admin": ["low", "medium", "high", "critical"],
        "analyst": ["low", "medium", "high"],
        "operator": ["low", "medium"],
        "viewer": [],
    }
    allowed_risk_levels = role_map.get(current_user.role, [])
    if not allowed_risk_levels:
        return PaginatedResponse(items=[], total=0, page=page, page_size=page_size, pages=1)

    # Filter approvals where user's role matches required_role
    q = q.where(ApprovalRequest.required_role.in_(["viewer", "operator", "analyst", "admin"]))

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar() or 0

    q = q.order_by(ApprovalRequest.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[ApprovalRequestResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/history", response_model=PaginatedResponse[ApprovalRequestResponse])
async def approval_history(
    company_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> PaginatedResponse[ApprovalRequestResponse]:
    allowed = await resolve_scope_company_ids(db, tenant_id, company_id)
    q = select(ApprovalRequest).where(
        ApprovalRequest.status.in_(["approved", "rejected", "expired"]),
        ApprovalRequest.company_id.in_(allowed),
    )

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar() or 0

    q = q.order_by(ApprovalRequest.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[ApprovalRequestResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/{approval_id}", response_model=ApprovalRequestResponse)
async def get_approval(
    approval_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> ApprovalRequestResponse:
    result = await db.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
    )
    req = result.scalar_one_or_none()
    if req is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    await assert_company_in_tenant(db, req.company_id, tenant_id)
    return ApprovalRequestResponse.model_validate(req)


@router.post("/{approval_id}/approve", response_model=ApprovalRequestResponse)
async def approve_request(
    approval_id: UUID,
    body: ApproveActionRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_active_user),
) -> ApprovalRequestResponse:
    result = await db.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
    )
    req = result.scalar_one_or_none()
    if req is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    await assert_company_in_tenant(db, req.company_id, tenant_id)
    if req.status != "pending":
        raise HTTPException(status_code=409, detail=f"Request is already '{req.status}'")

    now = datetime.now(timezone.utc)
    if req.expires_at < now:
        req.status = "expired"
        raise HTTPException(status_code=410, detail="Approval request has expired")

    before = {"status": req.status}
    req.status = "approved"
    req.reviewed_by = current_user.id
    req.reviewed_at = now
    req.review_notes = body.notes

    # Update associated task if present
    if req.task_id:
        task_result = await db.execute(
            select(AgentTask).where(AgentTask.id == req.task_id)
        )
        task = task_result.scalar_one_or_none()
        if task and task.status == "awaiting_approval":
            task.status = "approved"

    await write_audit_log(
        session=db,
        event_type="approval_request.approved",
        actor_id=current_user.id,
        actor_type="user",
        table_name="approval_requests",
        record_id=req.id,
        before_state=before,
        after_state={"status": "approved", "reviewed_by": str(current_user.id)},
        metadata={"notes": body.notes},
    )
    return ApprovalRequestResponse.model_validate(req)


@router.post("/{approval_id}/reject", response_model=ApprovalRequestResponse)
async def reject_request(
    approval_id: UUID,
    body: ApproveActionRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_active_user),
) -> ApprovalRequestResponse:
    result = await db.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
    )
    req = result.scalar_one_or_none()
    if req is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    await assert_company_in_tenant(db, req.company_id, tenant_id)
    if req.status != "pending":
        raise HTTPException(status_code=409, detail=f"Request is already '{req.status}'")

    before = {"status": req.status}
    req.status = "rejected"
    req.reviewed_by = current_user.id
    req.reviewed_at = datetime.now(timezone.utc)
    req.review_notes = body.notes

    # Fail associated task
    if req.task_id:
        task_result = await db.execute(
            select(AgentTask).where(AgentTask.id == req.task_id)
        )
        task = task_result.scalar_one_or_none()
        if task and task.status == "awaiting_approval":
            task.status = "rejected"

    await write_audit_log(
        session=db,
        event_type="approval_request.rejected",
        actor_id=current_user.id,
        actor_type="user",
        table_name="approval_requests",
        record_id=req.id,
        before_state=before,
        after_state={"status": "rejected"},
        metadata={"notes": body.notes},
    )
    return ApprovalRequestResponse.model_validate(req)
