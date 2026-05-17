"""Growth / scaling model tests."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.growth.scaling_model import build_plan, plan_vs_actual


def test_ramp_reaches_target_without_churn():
    plan = build_plan(
        metric_key="members",
        current_value=100,
        target_value=200,
        start=date(2026, 1, 1),
        deadline=date(2026, 4, 30),
        monthly_churn_rate=0.0,
    )
    assert plan.months == 4
    assert plan.ramp[-1].end_value == Decimal("200.00")
    # Linear trajectory: +25 net each month.
    assert plan.ramp[0].net_adds == Decimal("25.00")


def test_churn_makes_gross_exceed_net():
    plan = build_plan(
        metric_key="members",
        current_value=100,
        target_value=200,
        start=date(2026, 1, 1),
        deadline=date(2026, 6, 30),
        monthly_churn_rate=0.10,
    )
    for m in plan.ramp:
        assert m.gross_adds > m.net_adds
    assert plan.total_spend > 0


def test_capacity_gap_is_flagged():
    plan = build_plan(
        metric_key="members",
        current_value=200,
        target_value=1000,
        start=date(2026, 6, 1),
        deadline=date(2026, 12, 31),
        monthly_churn_rate=0.05,
        capacity_per_month=30,
    )
    assert plan.peak_monthly_gross_adds > 30
    assert any("CAPACITY GAP" in n for n in plan.feasibility_notes)


def test_crr_plan_reaches_1000():
    plan = build_plan(
        metric_key="active_members",
        current_value=200,
        target_value=1000,
        start=date(2026, 6, 1),
        deadline=date(2026, 12, 31),
        monthly_churn_rate=0.05,
    )
    assert plan.ramp[-1].end_value >= Decimal("999")
    assert len(plan.channels) == 3


def test_plan_vs_actual_marks_on_track():
    plan = build_plan(
        metric_key="members",
        current_value=100,
        target_value=160,
        start=date(2026, 1, 1),
        deadline=date(2026, 3, 31),
        monthly_churn_rate=0.0,
    )
    # Month 1 plan end is 120; an actual of 130 is ahead, 110 is behind.
    rows = plan_vs_actual(plan, {"2026-01": Decimal("130")})
    assert rows[0]["on_track"] is True
    assert rows[0]["actual_value"] == "130"
    assert rows[1]["actual_value"] is None
