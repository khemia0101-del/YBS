from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import assert_company_in_tenant, get_tenant_id, require_analyst
from app.models.financial import CashForecastRun, CashForecastWeek, StressTestRun
from app.schemas.cash import (
    ForecastRunResponse,
    ForecastWeekResponse,
    StressTestRequest,
    StressTestResponse,
)

router = APIRouter()


async def _load_forecast_in_tenant(
    db: AsyncSession, run_id: UUID, tenant_id: UUID
) -> CashForecastRun:
    result = await db.execute(
        select(CashForecastRun).where(CashForecastRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Forecast run not found")
    await assert_company_in_tenant(db, run.company_id, tenant_id)
    return run


@router.post("/forecast/run")
async def trigger_forecast(
    company_id: UUID = Query(...),
    beginning_cash: Decimal = Query(...),
    mode: str = Query("baseline"),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user=Depends(require_analyst),
) -> dict:
    """Trigger 13-week cash forecast via Celery."""
    await assert_company_in_tenant(db, company_id, tenant_id)
    try:
        from app.workers.financial_tasks import build_forecast

        task = build_forecast.delay(str(company_id), mode)
        return {
            "task_id": task.id,
            "company_id": str(company_id),
            "mode": mode,
            "status": "queued",
        }
    except Exception:
        from app.services.cash.forecast_builder import build_13_week_forecast

        run_id = await build_13_week_forecast(db, company_id, beginning_cash, mode)
        return {"run_id": str(run_id), "company_id": str(company_id), "status": "completed"}


@router.get("/forecast/{run_id}", response_model=ForecastRunResponse)
async def get_forecast(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> ForecastRunResponse:
    run = await _load_forecast_in_tenant(db, run_id, tenant_id)
    return ForecastRunResponse.model_validate(run)


@router.get("/forecast/{run_id}/weeks", response_model=list[ForecastWeekResponse])
async def get_forecast_weeks(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> list[ForecastWeekResponse]:
    await _load_forecast_in_tenant(db, run_id, tenant_id)
    result = await db.execute(
        select(CashForecastWeek)
        .where(CashForecastWeek.run_id == run_id)
        .order_by(CashForecastWeek.week_number)
    )
    weeks = result.scalars().all()
    return [ForecastWeekResponse.model_validate(w) for w in weeks]


@router.post("/stress-test/run", response_model=StressTestResponse)
async def run_stress_test(
    body: StressTestRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user=Depends(require_analyst),
) -> StressTestResponse:
    import uuid
    from datetime import date

    await assert_company_in_tenant(db, body.company_id, tenant_id)

    base_run_id = body.base_forecast_run_id
    if base_run_id is None and body.beginning_cash is not None:
        from app.services.cash.forecast_builder import build_13_week_forecast

        base_run_id = await build_13_week_forecast(
            db, body.company_id, body.beginning_cash, "baseline"
        )

    stress_params = {
        "revenue_reduction_pct": str(body.revenue_reduction_pct),
        "ar_delay_days": body.ar_delay_days,
        "payroll_increase_pct": str(body.payroll_increase_pct),
    }

    results: dict = {}
    if base_run_id:
        weeks_result = await db.execute(
            select(CashForecastWeek)
            .where(CashForecastWeek.run_id == base_run_id)
            .order_by(CashForecastWeek.week_number)
        )
        base_weeks = weeks_result.scalars().all()

        stressed_weeks = []
        for w in base_weeks:
            rev_reduction = Decimal(str(body.revenue_reduction_pct))
            ar = (w.ar_collections or Decimal("0")) * (1 - rev_reduction)
            payroll = (w.payroll_outflow or Decimal("0")) * (
                1 + Decimal(str(body.payroll_increase_pct))
            )
            net = ar - payroll - (w.overhead_outflow or Decimal("0"))
            stressed_weeks.append(
                {
                    "week_number": w.week_number,
                    "ar_collections": str(ar),
                    "payroll_outflow": str(payroll),
                    "net_cash_flow": str(net),
                }
            )
        results = {"weeks": stressed_weeks}

    run = StressTestRun(
        id=uuid.uuid4(),
        company_id=body.company_id,
        base_forecast_run_id=base_run_id,
        scenario_name=body.scenario_name,
        scenario_params=stress_params,
        results=results,
        run_date=date.today(),
        status="completed",
    )
    db.add(run)
    await db.flush()

    return StressTestResponse.model_validate(run)


@router.get("/stress-test/{run_id}", response_model=StressTestResponse)
async def get_stress_test(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> StressTestResponse:
    result = await db.execute(
        select(StressTestRun).where(StressTestRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Stress test run not found")
    await assert_company_in_tenant(db, run.company_id, tenant_id)
    return StressTestResponse.model_validate(run)


@router.get("/payroll-coverage")
async def get_payroll_coverage(
    company_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> dict:
    """Return the latest payroll coverage projection from the most recent forecast."""
    await assert_company_in_tenant(db, company_id, tenant_id)
    result = await db.execute(
        select(CashForecastRun)
        .where(CashForecastRun.company_id == company_id)
        .order_by(CashForecastRun.run_date.desc())
        .limit(1)
    )
    run = result.scalar_one_or_none()
    if run is None:
        return {"company_id": str(company_id), "payroll_covered_through": None}
    return {
        "company_id": str(company_id),
        "payroll_covered_through": run.payroll_covered_through.isoformat()
        if run.payroll_covered_through
        else None,
        "min_cash_amount": str(run.min_cash_amount) if run.min_cash_amount else None,
        "min_cash_week": run.min_cash_week,
        "forecast_run_id": str(run.id),
    }
