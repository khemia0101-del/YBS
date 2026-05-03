from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

MONEY_QUANTIZE = Decimal("0.01")


def to_money(value: float | str | Decimal | int) -> Decimal:
    """
    Convert any numeric value to a money-safe Decimal rounded to 2 decimal places.
    Always uses ROUND_HALF_UP (banker-safe for accounting).
    """
    return Decimal(str(value)).quantize(MONEY_QUANTIZE, rounding=ROUND_HALF_UP)


def money_add(*values: float | str | Decimal | int) -> Decimal:
    """Sum any number of values as money-safe Decimals."""
    return sum((to_money(v) for v in values), Decimal("0"))


def money_sub(a: float | str | Decimal, b: float | str | Decimal) -> Decimal:
    """Subtract b from a as money-safe Decimal."""
    return to_money(Decimal(str(a)) - Decimal(str(b)))


def money_mul(a: float | str | Decimal, b: float | str | Decimal) -> Decimal:
    """Multiply two values, returning a money-safe Decimal."""
    return to_money(Decimal(str(a)) * Decimal(str(b)))


def money_pct(part: Decimal, whole: Decimal, precision: int = 4) -> Decimal:
    """
    Calculate percentage (0-100) of part/whole.
    Returns Decimal rounded to `precision` decimal places.
    Returns Decimal("0") if whole is zero.
    """
    if whole == 0:
        return Decimal("0")
    quantize = Decimal(10) ** -precision
    return (part / whole * 100).quantize(quantize, rounding=ROUND_HALF_UP)
