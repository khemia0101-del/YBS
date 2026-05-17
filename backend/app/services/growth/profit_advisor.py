"""
Profitability recommendations engine.

Synthesizes the latest QoE run, KPI snapshots, and interview pain points into a
ranked, dollar-quantified set of profit-improvement recommendations. Rules-based
and deterministic so impact estimates are explainable; idempotent on rebuild.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import MetricDefinition, MetricSnapshot
from app.models.esop import QoERun
from app.models.interview import InterviewInsight
from app.models.profit import ProfitRecommendation

_Q = Decimal("0.01")


def _dec(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _money(value: Decimal) -> str:
    return f"${value:,.0f}"


async def _latest_qoe_primary(db: AsyncSession, company_id: UUID) -> dict | None:
    result = await db.execute(
        select(QoERun)
        .where(QoERun.company_id == company_id)
        .order_by(QoERun.run_date.desc(), QoERun.created_at.desc())
        .limit(1)
    )
    run = result.scalar_one_or_none()
    if run is None or not run.evidence_bundle:
        return None
    qoe = run.evidence_bundle.get("qoe", {})
    periods = qoe.get("periods", [])
    primary_label = qoe.get("primary_label")
    for p in periods:
        if p.get("label") == primary_label:
            return p
    return periods[-1] if periods else None


async def _latest_metric(db: AsyncSession, company_id: UUID, key: str) -> Decimal | None:
    result = await db.execute(
        select(MetricSnapshot.value)
        .join(
            MetricDefinition,
            MetricSnapshot.metric_definition_id == MetricDefinition.id,
        )
        .where(
            MetricDefinition.company_id == company_id,
            MetricDefinition.key == key,
        )
        .order_by(MetricSnapshot.period_date.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _candidates(db: AsyncSession, company_id: UUID) -> list[dict]:
    candidates: list[dict] = []
    primary = await _latest_qoe_primary(db, company_id)

    if primary:
        revenue = _dec(primary.get("revenue"))
        opex = _dec(primary.get("operating_expenses"))
        op_income = _dec(primary.get("operating_income"))
        gm = _dec(primary.get("gross_margin_pct"))

        if revenue > 0:
            pricing_impact = (revenue * Decimal("0.05")).quantize(_Q)
            candidates.append(
                {
                    "title": "Pricing optimization review",
                    "category": "pricing",
                    "description": (
                        f"Test a measured price increase. At a ~{gm:.0f}% gross margin, "
                        "incremental price flows almost entirely to the bottom line."
                    ),
                    "estimated_annual_impact": pricing_impact,
                    "effort": "low",
                    "confidence": "medium",
                    "rationale": f"A 5% increase on {_money(revenue)} of revenue.",
                }
            )

            op_margin = (op_income / revenue * 100) if revenue else Decimal("0")
            if op_margin < 5:
                cost_impact = (opex * Decimal("0.05")).quantize(_Q)
                candidates.append(
                    {
                        "title": "Operating-cost structure review",
                        "category": "cost_reduction",
                        "description": (
                            f"Operating margin is thin ({op_margin:.1f}%) despite a "
                            "strong gross margin — overhead is consuming the gross "
                            "profit. Run a line-by-line operating-expense review."
                        ),
                        "estimated_annual_impact": cost_impact,
                        "effort": "medium",
                        "confidence": "medium",
                        "rationale": f"Targeting a 5% cut on {_money(opex)} of operating expense.",
                    }
                )

            candidates.append(
                {
                    "title": "Expand upsell / cross-sell",
                    "category": "upsell",
                    "description": (
                        "Grow revenue per customer with add-on services or a higher "
                        "tier — expansion revenue carries little acquisition cost."
                    ),
                    "estimated_annual_impact": (revenue * Decimal("0.03")).quantize(_Q),
                    "effort": "medium",
                    "confidence": "low",
                    "rationale": "Conservative 3% revenue uplift from expansion revenue.",
                }
            )

    churn = await _latest_metric(db, company_id, "churn_rate")
    mrr = await _latest_metric(db, company_id, "mrr")
    if churn is not None and _dec(churn) > 3 and mrr is not None:
        impact = (_dec(mrr) * Decimal("0.01") * 12).quantize(_Q)
        candidates.append(
            {
                "title": "Churn reduction program",
                "category": "churn",
                "description": (
                    f"Monthly churn is {_dec(churn)}%. A retention program — structured "
                    "onboarding, proactive outreach, save offers — protects recurring "
                    "revenue at low cost."
                ),
                "estimated_annual_impact": impact,
                "effort": "medium",
                "confidence": "medium",
                "rationale": f"Retaining 1 point of monthly churn on {_money(_dec(mrr))} MRR.",
            }
        )

    pain_result = await db.execute(
        select(InterviewInsight).where(
            InterviewInsight.company_id == company_id,
            InterviewInsight.insight_type == "pain_point",
        )
    )
    for ins in pain_result.scalars().all():
        content = ins.content or {}
        if content.get("severity") in ("high", "medium"):
            candidates.append(
                {
                    "title": f"Address: {ins.title}"[:200],
                    "category": "margin",
                    "description": content.get("detail", ins.title),
                    "estimated_annual_impact": None,
                    "effort": "medium",
                    "confidence": "low",
                    "rationale": (
                        f"Surfaced as a {content.get('severity')} pain point in an "
                        "interview; impact to be quantified."
                    ),
                }
            )
    return candidates


async def build_recommendations(
    db: AsyncSession, company_id: UUID
) -> list[ProfitRecommendation]:
    """Refresh the company's profit-recommendation list; returns it impact-ranked."""
    candidates = await _candidates(db, company_id)

    existing_result = await db.execute(
        select(ProfitRecommendation).where(
            ProfitRecommendation.company_id == company_id
        )
    )
    existing = {r.title: r for r in existing_result.scalars().all()}

    for c in candidates:
        impact = c.get("estimated_annual_impact")
        impact = impact.quantize(_Q) if isinstance(impact, Decimal) else impact
        rec = existing.get(c["title"])
        if rec is None:
            rec = ProfitRecommendation(
                id=uuid.uuid4(),
                company_id=company_id,
                title=c["title"],
                description=c["description"],
                category=c["category"],
                estimated_annual_impact=impact,
                effort=c["effort"],
                confidence=c["confidence"],
                rationale=c["rationale"],
                status="proposed",
                source="rules",
            )
            db.add(rec)
            existing[c["title"]] = rec
        elif rec.status == "proposed":
            rec.description = c["description"]
            rec.category = c["category"]
            rec.estimated_annual_impact = impact
            rec.effort = c["effort"]
            rec.confidence = c["confidence"]
            rec.rationale = c["rationale"]
    await db.flush()

    result = await db.execute(
        select(ProfitRecommendation)
        .where(ProfitRecommendation.company_id == company_id)
        .order_by(
            func.coalesce(ProfitRecommendation.estimated_annual_impact, 0).desc()
        )
    )
    return list(result.scalars().all())
