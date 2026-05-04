from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_active_user, require_operator
from app.models.core import Contract
from app.models.financial import ProfitabilityRunLine
from app.models.transactions import LaborShift
from app.models.users import User
from app.schemas.common import PaginatedResponse
from app.schemas.financial import ProfitabilityRunLineResponse
from app.security.audit import write_audit_log

router = APIRouter()


@router.get("/")
async def list_contracts(
    company_id: UUID | None = Query(None),
    customer_id: UUID | None = Query(None),
    status: str | None = Query(None),
    contract_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
) -> dict:
    q = select(Contract)
    if customer_id:
        q = q.where(Contract.customer_id == customer_id)
    if status:
        q = q.where(Contract.status == status)
    if contract_type:
        q = q.where(Contract.contract_type == contract_type)

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar() or 0

    q = q.order_by(Contract.start_date.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    contracts = result.scalars().all()

    return {
        "items": [
            {
                "id": str(c.id),
                "customer_id": str(c.customer_id),
                "site_id": str(c.site_id) if c.site_id else None,
                "contract_number": c.contract_number,
                "start_date": c.start_date.isoformat(),
                "end_date": c.end_date.isoformat() if c.end_date else None,
                "monthly_value": str(c.monthly_value),
                "contract_type": c.contract_type,
                "status": c.status,
                "auto_renews": c.auto_renews,
                "scope_creep_flag": c.scope_creep_flag,
            }
            for c in contracts
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
    }


@router.get("/{contract_id}")
async def get_contract(
    contract_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
) -> dict:
    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalar_one_or_none()
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")

    return {
        "id": str(contract.id),
        "customer_id": str(contract.customer_id),
        "site_id": str(contract.site_id) if contract.site_id else None,
        "contract_number": contract.contract_number,
        "start_date": contract.start_date.isoformat(),
        "end_date": contract.end_date.isoformat() if contract.end_date else None,
        "monthly_value": str(contract.monthly_value),
        "scope_description": contract.scope_description,
        "service_frequency": contract.service_frequency,
        "contract_type": contract.contract_type,
        "auto_renews": contract.auto_renews,
        "renewal_notice_days": contract.renewal_notice_days,
        "status": contract.status,
        "qb_class": contract.qb_class,
        "scope_creep_flag": contract.scope_creep_flag,
        "scope_creep_details": contract.scope_creep_details,
        "confidence_score": str(contract.confidence_score) if contract.confidence_score else None,
        "created_at": contract.created_at.isoformat(),
        "updated_at": contract.updated_at.isoformat(),
    }


@router.get("/{contract_id}/profitability", response_model=ProfitabilityRunLineResponse | None)
async def get_contract_profitability(
    contract_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
) -> ProfitabilityRunLineResponse | None:
    result = await db.execute(
        select(ProfitabilityRunLine)
        .where(ProfitabilityRunLine.contract_id == contract_id)
        .order_by(ProfitabilityRunLine.created_at.desc())
        .limit(1)
    )
    line = result.scalar_one_or_none()
    if line is None:
        return None
    return ProfitabilityRunLineResponse.model_validate(line)


@router.get("/{contract_id}/labor-detail")
async def get_contract_labor_detail(
    contract_id: UUID,
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
) -> dict:
    q = select(LaborShift).where(LaborShift.contract_id == contract_id)
    if date_from:
        q = q.where(LaborShift.shift_date >= date_from)
    if date_to:
        q = q.where(LaborShift.shift_date <= date_to)

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar() or 0

    q = q.order_by(LaborShift.shift_date.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    shifts = result.scalars().all()

    total_hours = sum((s.hours_worked or 0 for s in shifts), 0)
    total_cost = sum((s.labor_cost or 0 for s in shifts), 0)

    return {
        "contract_id": str(contract_id),
        "summary": {
            "total_hours": str(total_hours),
            "total_cost": str(total_cost),
        },
        "items": [
            {
                "id": str(s.id),
                "employee_id": s.employee_id,
                "employee_name": s.employee_name,
                "shift_date": s.shift_date.isoformat(),
                "clock_in": s.clock_in.isoformat() if s.clock_in else None,
                "clock_out": s.clock_out.isoformat() if s.clock_out else None,
                "hours_worked": str(s.hours_worked) if s.hours_worked else None,
                "hourly_rate": str(s.hourly_rate) if s.hourly_rate else None,
                "labor_cost": str(s.labor_cost) if s.labor_cost else None,
                "worker_type": s.worker_type,
            }
            for s in shifts
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
    }


@router.post("/{contract_id}/flag-scope-creep")
async def flag_scope_creep(
    contract_id: UUID,
    details: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_operator),
) -> dict:
    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalar_one_or_none()
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")

    before = {"scope_creep_flag": contract.scope_creep_flag}
    contract.scope_creep_flag = True
    contract.scope_creep_details = details

    await write_audit_log(
        session=db,
        event_type="contract.scope_creep_flagged",
        actor_id=current_user.id,
        actor_type="user",
        table_name="contracts",
        record_id=contract.id,
        before_state=before,
        after_state={"scope_creep_flag": True, "details": details},
    )

    return {
        "contract_id": str(contract_id),
        "scope_creep_flag": True,
        "details": details,
        "flagged_at": datetime.now(timezone.utc).isoformat(),
    }
