"""
Baseline valuation.

Owner-operated small businesses are typically valued as a multiple of SDE.
Multiples vary with size, growth, margin, customer concentration, transferability,
and recurring-revenue mix. This produces a defensible low/mid/high range plus a
sensitivity table; it is a baseline, not a formal appraisal.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

_Q = Decimal("0.01")


def _d(value) -> Decimal:
    return (value if isinstance(value, Decimal) else Decimal(str(value))).quantize(_Q)


@dataclass
class ValuationResult:
    basis: str
    base_value: Decimal
    low_multiple: Decimal
    mid_multiple: Decimal
    high_multiple: Decimal
    low_value: Decimal
    mid_value: Decimal
    high_value: Decimal
    sensitivity: list[dict]
    rationale: list[str]

    def as_dict(self) -> dict:
        return {
            "basis": self.basis,
            "base_value": str(self.base_value),
            "low_multiple": str(self.low_multiple),
            "mid_multiple": str(self.mid_multiple),
            "high_multiple": str(self.high_multiple),
            "low_value": str(self.low_value),
            "mid_value": str(self.mid_value),
            "high_value": str(self.high_value),
            "sensitivity": self.sensitivity,
            "rationale": self.rationale,
        }


def value_by_sde(
    sde,
    low_multiple: float = 2.0,
    mid_multiple: float = 2.75,
    high_multiple: float = 3.5,
    rationale: list[str] | None = None,
) -> ValuationResult:
    """Value a business off SDE with a low/mid/high multiple range."""
    sde_d = _d(sde)
    lo, mid, hi = Decimal(str(low_multiple)), Decimal(str(mid_multiple)), Decimal(str(high_multiple))

    sensitivity = []
    m = lo
    step = Decimal("0.25")
    while m <= hi:
        sensitivity.append({"multiple": str(m), "value": str(_d(sde_d * m))})
        m += step

    return ValuationResult(
        basis="sde",
        base_value=sde_d,
        low_multiple=lo,
        mid_multiple=mid,
        high_multiple=hi,
        low_value=_d(sde_d * lo),
        mid_value=_d(sde_d * mid),
        high_value=_d(sde_d * hi),
        sensitivity=sensitivity,
        rationale=rationale or [],
    )
