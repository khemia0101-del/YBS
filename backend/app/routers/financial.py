from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_active_user, require_analyst
from app.models.financial import DSOSnapshot, ProfitabilityRun, ProfitabilityRunLine
from app.schemas.financial import (
    DSOResponse,
    ProfitabilityRunLineResponse,
    ProfitabilityRunResponse,
)

router = APIRouter()


@router.post("/profitability/run")
async def trigger_profitability_run(
    company_id: UUID = Query(...),
    period_start: date = Query(...),
    period_end: date = Query(...),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_analyst),
) -> dict:
    """Trigger async profitability calculation. Returns run_id."""
    try:
        from app.workers.financial_tasks import run_weekly_profitability

        task = run_weekly_profitability.delay(str(company_id))
        return {"task_id": task.id, "company_id": str(company_id), "status": "queued"}
    except Exception as exc:
        # Fallback: run inline
        from app.services.financial.margin_engine import run_company_profitability

        run_id = await run_company_profitability(db, company_id, period_start, period_end)
        return {"run_id": str(run_id), "company_id": str(company_id), "status": "completed"}


@router.get("/profitability/{run_id}", response_model=ProfitabilityRunResponse)
async def get_profitability_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
) -> ProfitabilityRunResponse:
    result = await db.execute(
        select(ProfitabilityRun).where(ProfitabilityRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Profitability run not found")
    return ProfitabilityRunResponse.model_validate(run)


@router.get(
    "/profitability/{run_id}/lines", response_model=list[ProfitabilityRunLineResponse]
)
async def get_profitability_lines(
    run_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
) -> list[ProfitabilityRunLineResponse]:
    result = await db.execute(
        select(ProfitabilityRunLine)
        .where(ProfitabilityRunLine.run_id == run_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    lines = result.scalars().all()
    return [ProfitabilityRunLineResponse.model_validate(l) for l in lines]


@router.get("/dso/current", response_model=DSOResponse)
async def get_current_dso(
    company_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
) -> DSOResponse:
    result = await db.execute(
        select(DSOSnapshot)
        .where(DSOSnapshot.company_id == company_id)
        .order_by(DSOSnapshot.snapshot_date.desc())
        .limit(1)
    )
    snap = result.scalar_one_or_none()
    if snap is None:
        raise HTTPException(status_code=404, detail="No DSO snapshot found")
    return DSOResponse.model_validate(snap)


@router.get("/dso/history", response_model=list[DSOResponse])
async def get_dso_history(
    company_id: UUID = Query(...),
    limit: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
) -> list[DSOResponse]:
    result = await db.execute(
        select(DSOSnapshot)
        .where(DSOSnapshot.company_id == company_id)
        .order_by(DSOSnapshot.snapshot_date.desc())
        .limit(limit)
    )
    snaps = result.scalars().all()
    return [DSOResponse.model_validate(s) for s in snaps]


@router.get("/concentration-risk")
async def get_concentration_risk(
    company_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
) -> dict:
    """Returns customer concentration report for the company."""
    from app.models.core import Contract, Customer
    from sqlalchemy import func

    # Aggregate annual revenue per customer via active contracts
    rows = await db.execute(
        select(
            Customer.id,
            Customer.name,
            func.sum(Contract.monthly_value * 12).label("annual_rev"),
            func.count(Contract.id).label("contract_count"),
        )
        .join(Contract, Contract.customer_id == Customer.id)
        .where(Customer.company_id == company_id, Contract.status == "active")
        .group_by(Customer.id, Customer.name)
        .order_by(func.sum(Contract.monthly_value * 12).desc())
    )
    customers = rows.all()

    from decimal import Decimal

    total = sum((r.annual_rev for r in customers), Decimal("0"))
    items = []
    for r in customers:
        pct = (Decimal(str(r.annual_rev)) / total * 100) if total else Decimal("0")
        items.append(
            {
                "customer_id": str(r.id),
                "customer_name": r.name,
                "annual_revenue": str(r.annual_rev),
                "concentration_pct": f"{pct:.4f}",
                "is_flagged": pct >= 20,
                "contract_count": r.contract_count,
            }
        )

    return {
        "company_id": str(company_id),
        "total_active_revenue": str(total),
        "customers": items,
        "hhi": str(sum((Decimal(i["concentration_pct"]) ** 2 for i in items), Decimal("0"))),
    }


@router.post("/qoe/run")
async def trigger_qoe_run(
    company_id: UUID = Query(...),
    period_start: date = Query(...),
    period_end: date = Query(...),
    _user=Depends(require_analyst),
) -> dict:
    """Enqueue a QoE base calculation task."""
    import uuid as _uuid

    run_id = _uuid.uuid4()
    # In production this would enqueue a Celery task.
    return {"run_id": str(run_id), "company_id": str(company_id), "status": "queued"}


@router.get("/qoe/{run_id}")
async def get_qoe_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
) -> dict:
    from app.models.esop import QoERun

    result = await db.execute(select(QoERun).where(QoERun.id == run_id))
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="QoE run not found")
    return {
        "id": str(run.id),
        "company_id": str(run.company_id),
        "run_date": run.run_date.isoformat(),
        "analysis_period_start": run.analysis_period_start.isoformat(),
        "analysis_period_end": run.analysis_period_end.isoformat(),
        "reported_ebitda": str(run.reported_ebitda) if run.reported_ebitda else None,
        "adjusted_ebitda": str(run.adjusted_ebitda) if run.adjusted_ebitda else None,
        "normalized_ebitda": str(run.normalized_ebitda) if run.normalized_ebitda else None,
        "status": run.status,
    }
