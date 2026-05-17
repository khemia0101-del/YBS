"""
Growth / scaling model.

Generic: given a north-star metric, its current value, a target, and a deadline,
it builds a monthly ramp (accounting for churn), allocates required gross adds
across acquisition channels with CAC and conversion assumptions, checks capacity,
and produces honest feasibility notes. Used for CRR's "1,000 members by Dec 2026"
goal and for any business with a configured growth goal.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

_Q = Decimal("0.01")


def _d(value) -> Decimal:
    return (value if isinstance(value, Decimal) else Decimal(str(value))).quantize(_Q)


@dataclass
class Channel:
    name: str
    share: float  # fraction of gross adds sourced from this channel (shares sum ~1)
    cac: float  # cost per acquired customer
    conversion_rate: float = 0.1  # leads -> customers


# Sensible default mix when a business has not configured its own channels.
DEFAULT_CHANNELS: list[Channel] = [
    Channel("Referral partners", share=0.45, cac=120.0, conversion_rate=0.25),
    Channel("Paid acquisition", share=0.40, cac=260.0, conversion_rate=0.06),
    Channel("Organic / affiliate", share=0.15, cac=60.0, conversion_rate=0.12),
]


@dataclass
class RampMonth:
    month: str
    start_value: Decimal
    churned: Decimal
    gross_adds: Decimal
    net_adds: Decimal
    end_value: Decimal
    spend: Decimal


@dataclass
class ScalingPlan:
    metric_key: str
    current_value: Decimal
    target_value: Decimal
    deadline: str
    months: int
    monthly_churn_rate: Decimal
    ramp: list[RampMonth]
    channels: list[dict]
    total_spend: Decimal
    peak_monthly_gross_adds: Decimal
    capacity_per_month: Decimal | None
    feasibility_notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "metric_key": self.metric_key,
            "current_value": str(self.current_value),
            "target_value": str(self.target_value),
            "deadline": self.deadline,
            "months": self.months,
            "monthly_churn_rate": str(self.monthly_churn_rate),
            "ramp": [
                {
                    "month": m.month,
                    "start_value": str(m.start_value),
                    "churned": str(m.churned),
                    "gross_adds": str(m.gross_adds),
                    "net_adds": str(m.net_adds),
                    "end_value": str(m.end_value),
                    "spend": str(m.spend),
                }
                for m in self.ramp
            ],
            "channels": self.channels,
            "total_spend": str(self.total_spend),
            "peak_monthly_gross_adds": str(self.peak_monthly_gross_adds),
            "capacity_per_month": str(self.capacity_per_month)
            if self.capacity_per_month is not None
            else None,
            "feasibility_notes": self.feasibility_notes,
        }


def _months_between(start: date, deadline: date) -> list[str]:
    """Inclusive list of YYYY-MM buckets from start's month through deadline's month."""
    months: list[str] = []
    y, m = start.year, start.month
    while (y, m) <= (deadline.year, deadline.month):
        months.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return months


def build_plan(
    metric_key: str,
    current_value,
    target_value,
    start: date,
    deadline: date,
    monthly_churn_rate: float = 0.0,
    channels: list[Channel] | None = None,
    capacity_per_month: float | None = None,
) -> ScalingPlan:
    """Build a month-by-month ramp from current_value to target_value by deadline."""
    current = _d(current_value)
    target = _d(target_value)
    churn = Decimal(str(monthly_churn_rate))
    channels = channels or DEFAULT_CHANNELS
    month_keys = _months_between(start, deadline)
    n = len(month_keys)
    if n == 0:
        raise ValueError("Deadline must be on or after the start date.")

    cac_blended = sum(Decimal(str(c.cac)) * Decimal(str(c.share)) for c in channels)

    ramp: list[RampMonth] = []
    running = current
    total_spend = Decimal("0")
    peak_gross = Decimal("0")
    for i, mkey in enumerate(month_keys, start=1):
        # Linear target trajectory to the deadline.
        target_end = current + (target - current) * Decimal(i) / Decimal(n)
        churned = (running * churn).quantize(_Q)
        gross_adds = (target_end - running + churned).quantize(_Q)
        if gross_adds < 0:
            gross_adds = Decimal("0")
        net_adds = (gross_adds - churned).quantize(_Q)
        end_value = (running + net_adds).quantize(_Q)
        spend = (gross_adds * cac_blended).quantize(_Q)
        ramp.append(
            RampMonth(mkey, running, churned, gross_adds, net_adds, end_value, spend)
        )
        running = end_value
        total_spend += spend
        peak_gross = max(peak_gross, gross_adds)

    # Per-channel allocation at peak demand.
    channel_rows: list[dict] = []
    for c in channels:
        ch_gross = (peak_gross * Decimal(str(c.share))).quantize(_Q)
        ch_spend = (ch_gross * Decimal(str(c.cac))).quantize(_Q)
        leads = (
            (ch_gross / Decimal(str(c.conversion_rate))).quantize(_Q)
            if c.conversion_rate
            else None
        )
        channel_rows.append(
            {
                "name": c.name,
                "share": c.share,
                "cac": str(_d(c.cac)),
                "peak_monthly_gross_adds": str(ch_gross),
                "peak_monthly_spend": str(ch_spend),
                "peak_monthly_leads_needed": str(leads) if leads is not None else None,
            }
        )

    notes: list[str] = []
    notes.append(
        f"Reaching {target} from {current} in {n} month(s) needs ~{peak_gross} gross "
        f"adds/month at peak (blended CAC ${cac_blended.quantize(_Q)})."
    )
    if capacity_per_month is not None and peak_gross > Decimal(str(capacity_per_month)):
        notes.append(
            f"CAPACITY GAP: peak demand of {peak_gross}/month exceeds the stated "
            f"capacity of {capacity_per_month}/month — staffing or process scale-up "
            "is required, not just marketing spend."
        )
    if churn > 0:
        notes.append(
            f"At {churn} monthly churn, gross adds must exceed net growth every month."
        )

    return ScalingPlan(
        metric_key=metric_key,
        current_value=current,
        target_value=target,
        deadline=deadline.isoformat(),
        months=n,
        monthly_churn_rate=churn,
        ramp=ramp,
        channels=channel_rows,
        total_spend=total_spend.quantize(_Q),
        peak_monthly_gross_adds=peak_gross,
        capacity_per_month=_d(capacity_per_month) if capacity_per_month is not None else None,
        feasibility_notes=notes,
    )


def plan_vs_actual(plan: ScalingPlan, actuals: dict[str, Decimal]) -> list[dict]:
    """Compare ramp targets to actual metric snapshots keyed by YYYY-MM."""
    rows: list[dict] = []
    for m in plan.ramp:
        actual = actuals.get(m.month)
        variance = (
            (actual - m.end_value).quantize(_Q) if actual is not None else None
        )
        rows.append(
            {
                "month": m.month,
                "planned_end_value": str(m.end_value),
                "actual_value": str(actual) if actual is not None else None,
                "variance": str(variance) if variance is not None else None,
                "on_track": (variance >= 0) if variance is not None else None,
            }
        )
    return rows
