"""
Unit tests for the contribution margin formula in margin_engine.
These tests use table-driven parameterization.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.utils.money import to_money


# ---------------------------------------------------------------------------
# Pure formula tests — no DB needed
# ---------------------------------------------------------------------------


def compute_margin(
    revenue: Decimal,
    w2_base_cost: Decimal,
    burden_pct: Decimal,
    sub_cost: Decimal,
    supplies: Decimal = Decimal("0"),
) -> tuple[Decimal, Decimal]:
    """
    Replication of the margin_engine formula for isolated unit testing.
    Returns (contribution_margin, contribution_margin_pct).
    """
    burden_cost = to_money(w2_base_cost * burden_pct)
    total_labor = to_money(w2_base_cost + burden_cost)
    contribution = to_money(revenue - total_labor - sub_cost - supplies)
    margin_pct = (
        to_money(contribution / revenue * 100) if revenue > 0 else Decimal("0")
    )
    return contribution, margin_pct


@pytest.mark.parametrize(
    "revenue, w2_base, burden_pct, sub_cost, expected_margin, expected_pct",
    [
        # Perfect scenario: high margin
        (
            Decimal("10000.00"),
            Decimal("5000.00"),
            Decimal("0.30"),
            Decimal("0"),
            Decimal("3500.00"),
            Decimal("35.00"),
        ),
        # Zero revenue
        (
            Decimal("0"),
            Decimal("5000.00"),
            Decimal("0.30"),
            Decimal("0"),
            Decimal("-6500.00"),
            Decimal("0"),  # pct is 0 when revenue=0
        ),
        # Negative margin (loss contract)
        (
            Decimal("5000.00"),
            Decimal("5000.00"),
            Decimal("0.30"),
            Decimal("500.00"),
            Decimal("-2000.00"),
            Decimal("-40.00"),
        ),
        # Subcontractor-only, no W2
        (
            Decimal("8000.00"),
            Decimal("0"),
            Decimal("0.30"),
            Decimal("6000.00"),
            Decimal("2000.00"),
            Decimal("25.00"),
        ),
        # Tiny rounding case
        (
            Decimal("100.00"),
            Decimal("33.33"),
            Decimal("0.30"),
            Decimal("0"),
            Decimal("56.67"),
            Decimal("56.67"),
        ),
        # Full burden (50%) high labor
        (
            Decimal("20000.00"),
            Decimal("12000.00"),
            Decimal("0.50"),
            Decimal("1000.00"),
            Decimal("1000.00"),
            Decimal("5.00"),
        ),
    ],
)
def test_contribution_margin_formula(
    revenue: Decimal,
    w2_base: Decimal,
    burden_pct: Decimal,
    sub_cost: Decimal,
    expected_margin: Decimal,
    expected_pct: Decimal,
) -> None:
    margin, pct = compute_margin(revenue, w2_base, burden_pct, sub_cost)
    assert margin == expected_margin, f"Expected margin {expected_margin}, got {margin}"
    assert pct == expected_pct, f"Expected pct {expected_pct}, got {pct}"


def test_to_money_rounds_half_up() -> None:
    """Ensure ROUND_HALF_UP is used (not banker's rounding)."""
    assert to_money(Decimal("0.125")) == Decimal("0.13")
    assert to_money(Decimal("0.135")) == Decimal("0.14")
    assert to_money(Decimal("0.005")) == Decimal("0.01")


def test_to_money_handles_float() -> None:
    result = to_money(1.005)
    assert result == Decimal("1.01")


def test_to_money_handles_string() -> None:
    result = to_money("12345.6789")
    assert result == Decimal("12345.68")


def test_margin_with_supplies() -> None:
    """Supplies cost reduces contribution margin."""
    revenue = Decimal("10000.00")
    w2 = Decimal("4000.00")
    burden = Decimal("0.30")
    sub = Decimal("0")
    supplies = Decimal("500.00")
    margin, pct = compute_margin(revenue, w2, burden, sub, supplies)
    # labor with burden = 4000 * 1.30 = 5200
    # contribution = 10000 - 5200 - 0 - 500 = 4300
    assert margin == Decimal("4300.00")
    assert pct == Decimal("43.00")
