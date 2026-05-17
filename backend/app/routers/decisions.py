from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import (
    assert_company_in_tenant,
    get_current_active_user,
    get_tenant_id,
    require_analyst,
    resolve_scope_company_ids,
)
from app.models.financial import Decision
from app.models.users import User
from app.schemas.common import PaginatedResponse
from app.schemas.decisions import BidScoreRequest, BidScoreResponse, DecisionResponse
from app.security.audit import write_audit_log
from app.utils.money import to_money

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[DecisionResponse])
async def list_decisions(
    company_id: UUID | None = Query(None),
    label: str | None = Query(None),
    status: str | None = Query(None),
    subject_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> PaginatedResponse[DecisionResponse]:
    allowed = await resolve_scope_company_ids(db, tenant_id, company_id)
    q = select(Decision).where(Decision.company_id.in_(allowed))
    if label:
        q = q.where(Decision.label == label)
    if status:
        q = q.where(Decision.status == status)
    if subject_type:
        q = q.where(Decision.subject_type == subject_type)

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar() or 0

    q = q.order_by(Decision.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[DecisionResponse.model_validate(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/recommendations", response_model=PaginatedResponse[DecisionResponse])
async def get_recommendations(
    company_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> PaginatedResponse[DecisionResponse]:
    """All APPROVAL_REQUIRED decisions pending review."""
    allowed = await resolve_scope_company_ids(db, tenant_id, company_id)
    q = select(Decision).where(
        Decision.label == "APPROVAL_REQUIRED",
        Decision.status == "pending",
        Decision.company_id.in_(allowed),
    )

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar() or 0

    q = q.order_by(Decision.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[DecisionResponse.model_validate(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/{decision_id}", response_model=DecisionResponse)
async def get_decision(
    decision_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> DecisionResponse:
    result = await db.execute(select(Decision).where(Decision.id == decision_id))
    decision = result.scalar_one_or_none()
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    await assert_company_in_tenant(db, decision.company_id, tenant_id)
    return DecisionResponse.model_validate(decision)


@router.post("/{decision_id}/approve", response_model=DecisionResponse)
async def approve_decision(
    decision_id: UUID,
    notes: str | None = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: User = Depends(require_analyst),
) -> DecisionResponse:
    result = await db.execute(select(Decision).where(Decision.id == decision_id))
    decision = result.scalar_one_or_none()
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    await assert_company_in_tenant(db, decision.company_id, tenant_id)
    if decision.status != "pending":
        raise HTTPException(status_code=409, detail=f"Decision is already '{decision.status}'")

    before = {"status": decision.status}
    decision.status = "approved"
    decision.approved_by = current_user.id
    decision.approved_at = datetime.now(timezone.utc)

    await write_audit_log(
        session=db,
        event_type="decision.approved",
        actor_id=current_user.id,
        actor_type="user",
        table_name="decisions",
        record_id=decision.id,
        before_state=before,
        after_state={"status": "approved"},
        metadata={"notes": notes},
    )
    return DecisionResponse.model_validate(decision)


@router.post("/{decision_id}/reject", response_model=DecisionResponse)
async def reject_decision(
    decision_id: UUID,
    notes: str | None = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: User = Depends(require_analyst),
) -> DecisionResponse:
    result = await db.execute(select(Decision).where(Decision.id == decision_id))
    decision = result.scalar_one_or_none()
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    await assert_company_in_tenant(db, decision.company_id, tenant_id)

    before = {"status": decision.status}
    decision.status = "rejected"

    await write_audit_log(
        session=db,
        event_type="decision.rejected",
        actor_id=current_user.id,
        actor_type="user",
        table_name="decisions",
        record_id=decision.id,
        before_state=before,
        after_state={"status": "rejected"},
        metadata={"notes": notes},
    )
    return DecisionResponse.model_validate(decision)


@router.post("/bid-score", response_model=BidScoreResponse)
async def score_bid(
    body: BidScoreRequest,
    _user=Depends(get_current_active_user),
) -> BidScoreResponse:
    """
    Ad-hoc bid scoring. Calculates contribution margin and returns
    a decision label without persisting to the database.
    """
    from app.config import settings as cfg

    # Estimate labor cost with burden
    labor_cost = to_money(body.estimated_hours_per_month * body.hourly_rate)
    burden_pct = Decimal("0.30")  # Default 30% burden — real impl uses LaborBurdenAssumption
    total_labor = to_money(labor_cost * (1 + burden_pct))
    sub_cost = to_money(body.proposed_monthly_value * body.subcontractor_pct)
    overhead = to_money(body.proposed_monthly_value * body.overhead_allocation_pct)
    contribution = to_money(body.proposed_monthly_value - total_labor - sub_cost - overhead)
    margin_pct = (
        to_money(contribution / body.proposed_monthly_value * 100)
        if body.proposed_monthly_value > 0
        else Decimal("0")
    )

    # Decision logic
    if margin_pct >= 20:
        decision_type = "bid"
        label = "AUTO"
        recommended_action = "Bid at proposed price — margin meets threshold"
    elif margin_pct >= 10:
        decision_type = "bid"
        label = "APPROVAL_REQUIRED"
        recommended_action = "Bid at proposed price — requires analyst approval (tight margin)"
    elif margin_pct >= 0:
        decision_type = "reprice"
        label = "APPROVAL_REQUIRED"
        recommended_price = to_money(
            (total_labor + sub_cost + overhead) / Decimal("0.80")
        )
        recommended_action = f"Reprice to ${recommended_price}/month to achieve 20% margin"
        return BidScoreResponse(
            decision_type=decision_type,
            label=label,
            recommended_price=recommended_price,
            contribution_margin=contribution,
            contribution_margin_pct=margin_pct,
            rationale={
                "labor_cost": str(labor_cost),
                "burden_cost": str(total_labor - labor_cost),
                "subcontractor_cost": str(sub_cost),
                "overhead": str(overhead),
                "margin_pct": str(margin_pct),
            },
            recommended_action=recommended_action,
        )
    else:
        decision_type = "no_bid"
        label = "BLOCKED"
        recommended_action = "Do not bid — negative contribution margin"

    # Calculate recommended price for positive margin scenarios
    recommended_price = to_money(
        (total_labor + sub_cost + overhead) / Decimal("0.80")
    )

    return BidScoreResponse(
        decision_type=decision_type,
        label=label,
        recommended_price=recommended_price,
        contribution_margin=contribution,
        contribution_margin_pct=margin_pct,
        rationale={
            "labor_cost": str(labor_cost),
            "burden_cost": str(total_labor - labor_cost),
            "subcontractor_cost": str(sub_cost),
            "overhead": str(overhead),
            "margin_pct": str(margin_pct),
        },
        recommended_action=recommended_action,
    )
