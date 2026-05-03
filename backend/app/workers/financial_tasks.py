from __future__ import annotations

import asyncio
from datetime import date, timedelta

from app.workers.celery_app import app as celery_app


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.workers.financial_tasks.run_weekly_profitability")
def run_weekly_profitability(company_id: str | None = None) -> dict:
    """
    Run profitability calculation for the prior calendar month.
    If company_id is None, runs for all active companies.
    """
    return _run_async(_run_profitability_async(company_id))


async def _run_profitability_async(company_id_str: str | None) -> dict:
    import uuid
    from app.database import AsyncSessionLocal
    from app.services.financial.margin_engine import run_company_profitability

    # Prior month date range
    today = date.today()
    period_end = today.replace(day=1) - timedelta(days=1)
    period_start = period_end.replace(day=1)

    results = {}

    async with AsyncSessionLocal() as session:
        if company_id_str:
            company_ids = [uuid.UUID(company_id_str)]
        else:
            from app.models.core import Company
            from sqlalchemy import select

            all_cos = await session.execute(select(Company.id))
            company_ids = [row[0] for row in all_cos]

        for cid in company_ids:
            try:
                run_id = await run_company_profitability(
                    session, cid, period_start, period_end
                )
                await session.commit()
                results[str(cid)] = {"run_id": str(run_id), "status": "ok"}
            except Exception as exc:
                await session.rollback()
                results[str(cid)] = {"status": "error", "error": str(exc)}

    return {"period_start": period_start.isoformat(), "period_end": period_end.isoformat(), **results}


@celery_app.task(name="app.workers.financial_tasks.run_daily_dso")
def run_daily_dso(company_id: str | None = None) -> dict:
    """Compute a DSO snapshot for today for all (or specified) companies."""
    return _run_async(_run_dso_async(company_id))


async def _run_dso_async(company_id_str: str | None) -> dict:
    import uuid
    from app.database import AsyncSessionLocal
    from app.services.financial.dso_engine import compute_dso

    today = date.today()
    results = {}

    async with AsyncSessionLocal() as session:
        if company_id_str:
            company_ids = [uuid.UUID(company_id_str)]
        else:
            from app.models.core import Company
            from sqlalchemy import select

            all_cos = await session.execute(select(Company.id))
            company_ids = [row[0] for row in all_cos]

        for cid in company_ids:
            try:
                snap = await compute_dso(session, cid, today)
                await session.commit()
                results[str(cid)] = {
                    "snapshot_id": str(snap.id),
                    "dso_days": str(snap.dso_days),
                    "status": "ok",
                }
            except Exception as exc:
                await session.rollback()
                results[str(cid)] = {"status": "error", "error": str(exc)}

    return {"date": today.isoformat(), **results}


@celery_app.task(name="app.workers.financial_tasks.build_forecast")
def build_forecast(company_id: str, mode: str = "baseline") -> str:
    """Build a 13-week cash forecast. Returns the forecast run_id as string."""
    return _run_async(_build_forecast_async(company_id, mode))


async def _build_forecast_async(company_id_str: str, mode: str) -> str:
    import uuid
    from decimal import Decimal
    from app.database import AsyncSessionLocal
    from app.services.cash.forecast_builder import build_13_week_forecast

    cid = uuid.UUID(company_id_str)

    async with AsyncSessionLocal() as session:
        # Default beginning_cash = 0 (should be overridden by caller via API)
        run_id = await build_13_week_forecast(
            session, cid, Decimal("0"), mode
        )
        await session.commit()

    return str(run_id)
