"""Quality-of-Earnings engine + valuation tests."""
from __future__ import annotations

from decimal import Decimal

from app.services.qoe.crr_data import CRR_PERIODS
from app.services.qoe.engine import Addback, FinancialPeriod, analyze, analyze_period
from app.services.qoe.valuation import value_by_sde


def test_period_math_basic():
    p = FinancialPeriod(
        label="Y1",
        revenue="1000",
        cogs="100",
        operating_expenses="700",
        addbacks=[
            Addback("One-time", "50", applies_to="ebitda", category="non_recurring"),
            Addback("Owner comp", "200", applies_to="sde", category="owner_comp"),
        ],
    )
    r = analyze_period(p)
    assert r.gross_profit == Decimal("900.00")
    assert r.gross_margin_pct == Decimal("90.00")
    assert r.operating_income == Decimal("200.00")
    assert r.reported_ebitda == Decimal("200.00")
    assert r.adjusted_ebitda == Decimal("250.00")  # + ebitda addback
    assert r.sde == Decimal("450.00")  # adjusted ebitda + sde addback


def test_partial_period_is_annualized():
    p = FinancialPeriod(
        label="H1", revenue="600", cogs="0", operating_expenses="300", months=6
    )
    r = analyze_period(p)
    assert r.operating_income == Decimal("300.00")
    assert r.annualized_revenue == Decimal("1200.00")
    assert r.annualized_sde == Decimal("600.00")


def test_crr_fy2024_sde_and_valuation():
    qoe = analyze(CRR_PERIODS, primary_label="FY2024")
    fy24 = qoe.primary

    assert fy24.revenue == Decimal("323083.07")
    assert fy24.gross_profit == Decimal("314583.18")
    assert fy24.operating_income == Decimal("4044.51")
    assert fy24.reported_ebitda == Decimal("4044.51")
    # 36000 + 4020 + 3650.80 + 1796.67 = 45467.47
    assert fy24.sde == Decimal("49511.98")

    valuation = value_by_sde(fy24.sde, 2.0, 2.75, 3.5)
    assert valuation.low_value == Decimal("99023.96")
    assert valuation.mid_value == Decimal("136157.94")
    assert valuation.high_value == Decimal("173291.93")


def test_crr_revenue_cagr_is_positive():
    qoe = analyze(CRR_PERIODS, primary_label="FY2024")
    # FY2023 -> FY2024 growth, positive but small.
    assert qoe.revenue_cagr_pct is not None
    assert Decimal("0") < qoe.revenue_cagr_pct < Decimal("5")


def test_fy2023_non_recurring_addback_lifts_adjusted_ebitda():
    qoe = analyze(CRR_PERIODS, primary_label="FY2024")
    fy23 = next(r for r in qoe.periods if r.label == "FY2023")
    # FY2023 operating income is negative; the $10,862.46 prior-period
    # adjustment is an EBITDA-level addback.
    assert fy23.reported_ebitda == Decimal("-10239.41")
    assert fy23.ebitda_addbacks == Decimal("10862.46")
    assert fy23.adjusted_ebitda == Decimal("623.05")
