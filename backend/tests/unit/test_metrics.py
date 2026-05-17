"""KPI metrics engine tests."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.models.business import MetricDefinition, MetricSnapshot
from app.services.metrics.engine import build_kpi_summary


async def _metric(db, company_id, key, *, target=None, north_star=False):
    m = MetricDefinition(
        id=uuid.uuid4(),
        company_id=company_id,
        key=key,
        name=key.replace("_", " ").title(),
        unit="count",
        target_value=Decimal(str(target)) if target is not None else None,
        is_north_star=north_star,
    )
    db.add(m)
    await db.flush()
    return m


async def _snapshot(db, company_id, metric_id, period_dt, value):
    db.add(
        MetricSnapshot(
            id=uuid.uuid4(),
            company_id=company_id,
            metric_definition_id=metric_id,
            period_date=period_dt,
            period_type="monthly",
            value=Decimal(str(value)),
            source="manual",
        )
    )
    await db.flush()


@pytest.mark.asyncio
async def test_kpi_summary_computes_change_and_progress(db_session, sample_company):
    m = await _metric(
        db_session, sample_company.id, "active_members", target=1000, north_star=True
    )
    await _snapshot(db_session, sample_company.id, m.id, date(2025, 1, 1), 200)
    await _snapshot(db_session, sample_company.id, m.id, date(2025, 2, 1), 250)

    summary = await build_kpi_summary(db_session, sample_company.id)
    assert len(summary) == 1
    row = summary[0]
    assert row["key"] == "active_members"
    assert row["current_value"] == "250"
    assert row["previous_value"] == "200"
    assert row["change_pct"] == "25.00"
    assert row["progress_pct"] == "25.00"
    assert len(row["history"]) == 2
    # History is oldest-first.
    assert row["history"][0]["value"] == "200"


@pytest.mark.asyncio
async def test_kpi_summary_orders_north_star_first(db_session, sample_company):
    await _metric(db_session, sample_company.id, "gross_margin")
    await _metric(db_session, sample_company.id, "active_members", north_star=True)

    summary = await build_kpi_summary(db_session, sample_company.id)
    assert summary[0]["key"] == "active_members"
    assert summary[0]["is_north_star"] is True


@pytest.mark.asyncio
async def test_kpi_summary_handles_metric_with_no_snapshots(db_session, sample_company):
    await _metric(db_session, sample_company.id, "churn_rate")
    summary = await build_kpi_summary(db_session, sample_company.id)
    assert summary[0]["current_value"] is None
    assert summary[0]["change_pct"] is None
    assert summary[0]["history"] == []
