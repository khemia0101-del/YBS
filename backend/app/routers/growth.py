"""Growth / scaling plan — builds the ramp from the business profile's growth goal."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import assert_company_in_tenant, get_tenant_id
from app.models.business import MetricDefinition, MetricSnapshot
from app.services.business.profile import get_or_create_profile
from app.services.growth.scaling_model import (
    DEFAULT_CHANNELS,
    Channel,
    build_plan,
    plan_vs_actual,
)

router = APIRouter()


def _channels_from_config(config: dict | None) -> list[Channel]:
    raw = (config or {}).get("growth_channels")
    if not raw:
        return DEFAULT_CHANNELS
    return [
        Channel(
            name=c["name"],
            share=float(c.get("share", 0)),
            cac=float(c.get("cac", 0)),
            conversion_rate=float(c.get("conversion_rate", 0.1)),
        )
        for c in raw
    ]


async def _plan_for_company(db: AsyncSession, company_id: UUID):
    profile = await get_or_create_profile(db, company_id)
    goal = profile.growth_goal or {}
    if not goal.get("target_value") or not goal.get("deadline"):
        raise HTTPException(
            status_code=400,
            detail="No growth goal configured — set growth_goal on the business profile.",
        )
    config = profile.config or {}
    return build_plan(
        metric_key=goal.get("metric_key", profile.north_star_metric or "north_star"),
        current_value=goal.get("current_value", 0),
        target_value=goal["target_value"],
        start=date.today(),
        deadline=date.fromisoformat(goal["deadline"]),
        monthly_churn_rate=float(config.get("monthly_churn_rate", 0.0)),
        channels=_channels_from_config(config),
        capacity_per_month=config.get("capacity_per_month"),
    )


@router.get("/plan")
async def growth_plan(
    company_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> dict:
    """The monthly ramp from current value to the configured target."""
    await assert_company_in_tenant(db, company_id, tenant_id)
    plan = await _plan_for_company(db, company_id)
    return plan.as_dict()


@router.get("/tracker")
async def growth_tracker(
    company_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> dict:
    """Planned ramp vs. actual metric snapshots for the north-star metric."""
    await assert_company_in_tenant(db, company_id, tenant_id)
    plan = await _plan_for_company(db, company_id)

    metric_result = await db.execute(
        select(MetricDefinition).where(
            MetricDefinition.company_id == company_id,
            MetricDefinition.key == plan.metric_key,
        )
    )
    metric = metric_result.scalar_one_or_none()
    actuals: dict[str, Decimal] = {}
    if metric is not None:
        snap_result = await db.execute(
            select(MetricSnapshot).where(
                MetricSnapshot.metric_definition_id == metric.id
            )
        )
        for s in snap_result.scalars().all():
            actuals[s.period_date.strftime("%Y-%m")] = s.value

    return {
        "metric_key": plan.metric_key,
        "deadline": plan.deadline,
        "comparison": plan_vs_actual(plan, actuals),
        "feasibility_notes": plan.feasibility_notes,
    }
