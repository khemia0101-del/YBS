"""
Quality-of-Earnings engine.

Generic, vertical-agnostic: given annual financial periods plus an addback
schedule, it computes gross margin, reported EBITDA, an EBITDA->SDE bridge, and
revenue-quality / trend signals. Used for the CRR baseline report and for any
business onboarded later.

Addback conventions
-------------------
Each addback has ``applies_to``:
  * ``"ebitda"`` — non-recurring or normalizing items; flow into Adjusted EBITDA
    (and therefore SDE).
  * ``"sde"`` — owner compensation, owner-discretionary spend, related-party and
    financing items; flow into SDE only.
SDE (Seller's Discretionary Earnings) is the total annual benefit to a single
owner-operator — the standard basis for valuing an owner-run small business.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

_Q = Decimal("0.01")


def _d(value) -> Decimal:
    return (value if isinstance(value, Decimal) else Decimal(str(value))).quantize(_Q)


@dataclass
class Addback:
    label: str
    amount: Decimal
    applies_to: str  # "ebitda" | "sde"
    category: str  # non_recurring | related_party | owner_comp | discretionary | financing
    rationale: str = ""
    confidence: str = "medium"  # high | medium | low — diligence confidence

    def __post_init__(self) -> None:
        self.amount = _d(self.amount)


@dataclass
class FinancialPeriod:
    label: str
    revenue: Decimal
    cogs: Decimal
    operating_expenses: Decimal
    interest: Decimal = Decimal("0")
    depreciation: Decimal = Decimal("0")
    amortization: Decimal = Decimal("0")
    net_income: Decimal | None = None
    months: int = 12
    addbacks: list[Addback] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self) -> None:
        self.revenue = _d(self.revenue)
        self.cogs = _d(self.cogs)
        self.operating_expenses = _d(self.operating_expenses)
        self.interest = _d(self.interest)
        self.depreciation = _d(self.depreciation)
        self.amortization = _d(self.amortization)
        if self.net_income is not None:
            self.net_income = _d(self.net_income)

    @classmethod
    def from_payload(cls, data: dict) -> FinancialPeriod:
        addbacks = [Addback(**a) for a in data.get("addbacks", [])]
        return cls(
            label=data["label"],
            revenue=_d(data["revenue"]),
            cogs=_d(data.get("cogs", 0)),
            operating_expenses=_d(data.get("operating_expenses", 0)),
            interest=_d(data.get("interest", 0)),
            depreciation=_d(data.get("depreciation", 0)),
            amortization=_d(data.get("amortization", 0)),
            net_income=None if data.get("net_income") is None else _d(data["net_income"]),
            months=int(data.get("months", 12)),
            addbacks=addbacks,
            notes=data.get("notes", ""),
        )


@dataclass
class PeriodResult:
    label: str
    months: int
    revenue: Decimal
    cogs: Decimal
    gross_profit: Decimal
    gross_margin_pct: Decimal
    operating_expenses: Decimal
    operating_income: Decimal
    reported_ebitda: Decimal
    ebitda_addbacks: Decimal
    adjusted_ebitda: Decimal
    sde_addbacks: Decimal
    sde: Decimal
    sde_margin_pct: Decimal
    annualized_revenue: Decimal
    annualized_sde: Decimal

    def as_dict(self) -> dict:
        return {k: (str(v) if isinstance(v, Decimal) else v) for k, v in vars(self).items()}


def analyze_period(p: FinancialPeriod) -> PeriodResult:
    gross_profit = p.revenue - p.cogs
    gross_margin = (gross_profit / p.revenue * 100) if p.revenue else Decimal("0")
    operating_income = gross_profit - p.operating_expenses
    reported_ebitda = operating_income + p.depreciation + p.amortization

    ebitda_addbacks = sum(
        (a.amount for a in p.addbacks if a.applies_to == "ebitda"), Decimal("0")
    )
    adjusted_ebitda = reported_ebitda + ebitda_addbacks
    sde_addbacks = sum(
        (a.amount for a in p.addbacks if a.applies_to == "sde"), Decimal("0")
    )
    sde = adjusted_ebitda + sde_addbacks
    sde_margin = (sde / p.revenue * 100) if p.revenue else Decimal("0")

    factor = Decimal(12) / Decimal(p.months) if p.months else Decimal(1)
    return PeriodResult(
        label=p.label,
        months=p.months,
        revenue=_d(p.revenue),
        cogs=_d(p.cogs),
        gross_profit=_d(gross_profit),
        gross_margin_pct=_d(gross_margin),
        operating_expenses=_d(p.operating_expenses),
        operating_income=_d(operating_income),
        reported_ebitda=_d(reported_ebitda),
        ebitda_addbacks=_d(ebitda_addbacks),
        adjusted_ebitda=_d(adjusted_ebitda),
        sde_addbacks=_d(sde_addbacks),
        sde=_d(sde),
        sde_margin_pct=_d(sde_margin),
        annualized_revenue=_d(p.revenue * factor),
        annualized_sde=_d(sde * factor),
    )


@dataclass
class QoEResult:
    periods: list[PeriodResult]
    primary_label: str  # the most recent full year — the valuation basis
    revenue_cagr_pct: Decimal | None
    notes: list[str]

    @property
    def primary(self) -> PeriodResult:
        return next(r for r in self.periods if r.label == self.primary_label)

    def as_dict(self) -> dict:
        return {
            "periods": [r.as_dict() for r in self.periods],
            "primary_label": self.primary_label,
            "revenue_cagr_pct": str(self.revenue_cagr_pct)
            if self.revenue_cagr_pct is not None
            else None,
            "notes": self.notes,
        }


def analyze(periods: list[FinancialPeriod], primary_label: str | None = None) -> QoEResult:
    """Run the QoE analysis across all periods."""
    if not periods:
        raise ValueError("At least one financial period is required.")
    results = [analyze_period(p) for p in periods]

    full_years = [r for r in results if r.months == 12]
    primary = primary_label or (full_years[-1].label if full_years else results[-1].label)

    # Revenue CAGR across full years (annualized).
    cagr: Decimal | None = None
    if len(full_years) >= 2:
        first, last = full_years[0], full_years[-1]
        if first.revenue > 0:
            years = Decimal(len(full_years) - 1)
            ratio = last.revenue / first.revenue
            cagr = _d((ratio ** (1 / years) - 1) * 100)

    notes: list[str] = []
    for r in results:
        if r.months != 12:
            notes.append(
                f"{r.label}: partial period ({r.months} mo) — shown at annualized run rate."
            )
    return QoEResult(periods=results, primary_label=primary, revenue_cagr_pct=cagr, notes=notes)
