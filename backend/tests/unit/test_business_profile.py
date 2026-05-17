"""Adaptive business profile tests."""
from __future__ import annotations

import pytest

from app.models.business import MetricDefinition
from app.services.business.profile import (
    CREDIT_REPAIR_METRICS,
    build_metric_definitions,
    get_or_create_profile,
)


@pytest.mark.asyncio
async def test_get_or_create_profile_is_idempotent(db_session, sample_company):
    p1 = await get_or_create_profile(db_session, sample_company.id)
    p2 = await get_or_create_profile(db_session, sample_company.id)
    assert p1.id == p2.id
    assert p1.company_id == sample_company.id


@pytest.mark.asyncio
async def test_build_metric_definitions_from_template(db_session, sample_company):
    profile = await get_or_create_profile(db_session, sample_company.id)
    metrics = build_metric_definitions(
        sample_company.id, profile.id, CREDIT_REPAIR_METRICS
    )
    assert len(metrics) == len(CREDIT_REPAIR_METRICS)
    assert all(isinstance(m, MetricDefinition) for m in metrics)
    assert all(m.company_id == sample_company.id for m in metrics)
    assert all(m.profile_id == profile.id for m in metrics)

    north_stars = [m for m in metrics if m.is_north_star]
    assert len(north_stars) == 1
    assert north_stars[0].key == "active_members"


def test_credit_repair_template_keys_unique():
    keys = [m["key"] for m in CREDIT_REPAIR_METRICS]
    assert len(keys) == len(set(keys))
