"""
KPI metrics engine.

Reads whatever ``MetricDefinition`` rows a business has configured (Phase 1) and
rolls their ``MetricSnapshot`` history into a dashboard-ready summary: current
value, prior value, period-over-period change, and progress toward target.
Vertical-agnostic — it works off the configured metrics, not a hardcoded set.
"""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import MetricDefinition, MetricSnapshot

_Q = Decimal("0.01")


def _fmt(value: Decimal | None) -> str | None:
    """Render a metric value without trailing zeros or exponent notation."""
    if value is None:
        return None
    normalized = value.normalize()
    return f"{normalized:f}"


def _pct_change(current: Decimal, previous: Decimal) -> Decimal | None:
    if previous == 0:
        return None
    return ((current - previous) / abs(previous) * 100).quantize(_Q)


async def build_kpi_summary(
    db: AsyncSession, company_id: UUID, history_limit: int = 12
) -> list[dict]:
    """Return one summary dict per active metric, north-star metrics first."""
    defs_result = await db.execute(
        select(MetricDefinition)
        .where(
            MetricDefinition.company_id == company_id,
            MetricDefinition.is_active.is_(True),
        )
        .order_by(MetricDefinition.is_north_star.desc(), MetricDefinition.name)
    )
    definitions = defs_result.scalars().all()

    summaries: list[dict] = []
    for d in definitions:
        snap_result = await db.execute(
            select(MetricSnapshot)
            .where(MetricSnapshot.metric_definition_id == d.id)
            .order_by(MetricSnapshot.period_date.desc())
            .limit(history_limit)
        )
        snapshots = snap_result.scalars().all()

        current = snapshots[0].value if snapshots else None
        previous = snapshots[1].value if len(snapshots) > 1 else None
        change_pct = (
            _pct_change(current, previous)
            if current is not None and previous is not None
            else None
        )
        progress_pct = (
            (current / d.target_value * 100).quantize(_Q)
            if current is not None and d.target_value and d.target_value != 0
            else None
        )

        summaries.append(
            {
                "metric_id": str(d.id),
                "key": d.key,
                "name": d.name,
                "unit": d.unit,
                "category": d.category,
                "is_north_star": d.is_north_star,
                "current_value": _fmt(current),
                "previous_value": _fmt(previous),
                "change_pct": str(change_pct) if change_pct is not None else None,
                "target_value": _fmt(d.target_value),
                "progress_pct": str(progress_pct) if progress_pct is not None else None,
                "latest_period": snapshots[0].period_date.isoformat() if snapshots else None,
                "history": [
                    {"period_date": s.period_date.isoformat(), "value": _fmt(s.value)}
                    for s in reversed(snapshots)
                ],
            }
        )
    return summaries
