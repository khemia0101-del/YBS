"""Profitability recommendations engine tests."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.models.esop import QoERun
from app.services.growth.profit_advisor import build_recommendations


async def _seed_qoe(db, company_id, revenue, opex, op_income):
    db.add(
        QoERun(
            id=uuid.uuid4(),
            company_id=company_id,
            run_date=date(2025, 1, 1),
            analysis_period_start=date(2024, 1, 1),
            analysis_period_end=date(2024, 12, 31),
            status="draft",
            evidence_bundle={
                "qoe": {
                    "primary_label": "FY2024",
                    "periods": [
                        {
                            "label": "FY2024",
                            "revenue": str(revenue),
                            "operating_expenses": str(opex),
                            "operating_income": str(op_income),
                            "gross_margin_pct": "95",
                        }
                    ],
                }
            },
        )
    )
    await db.flush()


@pytest.mark.asyncio
async def test_build_recommendations_from_qoe(db_session, sample_company):
    await _seed_qoe(db_session, sample_company.id, 300000, 280000, 5000)
    recs = await build_recommendations(db_session, sample_company.id)

    titles = {r.title for r in recs}
    assert "Pricing optimization review" in titles
    assert "Operating-cost structure review" in titles
    assert "Expand upsell / cross-sell" in titles

    pricing = next(r for r in recs if r.title == "Pricing optimization review")
    assert pricing.estimated_annual_impact == Decimal("15000.00")  # 5% of 300k

    impacts = [r.estimated_annual_impact or Decimal("0") for r in recs]
    assert impacts == sorted(impacts, reverse=True)


@pytest.mark.asyncio
async def test_build_recommendations_is_idempotent(db_session, sample_company):
    await _seed_qoe(db_session, sample_company.id, 300000, 280000, 5000)
    first = await build_recommendations(db_session, sample_company.id)
    second = await build_recommendations(db_session, sample_company.id)
    assert len(first) == len(second)
    assert {r.title for r in first} == {r.title for r in second}


@pytest.mark.asyncio
async def test_no_cost_rec_when_operating_margin_is_healthy(db_session, sample_company):
    # 60k operating income on 300k revenue = 20% margin — no cost-reduction rec.
    await _seed_qoe(db_session, sample_company.id, 300000, 240000, 60000)
    recs = await build_recommendations(db_session, sample_company.id)
    titles = {r.title for r in recs}
    assert "Operating-cost structure review" not in titles
    assert "Pricing optimization review" in titles
