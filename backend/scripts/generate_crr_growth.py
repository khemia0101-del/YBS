#!/usr/bin/env python3
"""
Generate the CRR scaling plan into docs/growth/crr-scaling-plan.md.

Models the path from ~200 active members to 1,000 by 2026-12-31.

Usage:
    cd backend && python scripts/generate_crr_growth.py
"""
from __future__ import annotations

import os
import sys
from datetime import date
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.growth.scaling_model import build_plan  # noqa: E402


def _money(v) -> str:
    return f"${Decimal(str(v)):,.0f}"


def render(plan) -> str:
    lines: list[str] = []
    a = lines.append
    a("# Scaling Plan — Credit Repair Resources LLC")
    a("")
    a(f"*Generated {date.today().isoformat()}. Goal: grow the active-member base "
      f"to {plan.target_value} by {plan.deadline}.*")
    a("")
    a("## Summary")
    a("")
    a(f"- **Current active members:** {plan.current_value}")
    a(f"- **Target:** {plan.target_value} by {plan.deadline}")
    a(f"- **Window:** {plan.months} months")
    a(f"- **Peak gross adds required:** {plan.peak_monthly_gross_adds} / month")
    a(f"- **Estimated total acquisition spend:** {_money(plan.total_spend)}")
    a(f"- **Assumed monthly churn:** {plan.monthly_churn_rate}")
    a("")
    a("## Monthly ramp")
    a("")
    a("| Month | Start | Churned | Gross adds | Net adds | End | Spend |")
    a("|---|---|---|---|---|---|---|")
    for m in plan.ramp:
        a(f"| {m.month} | {m.start_value} | {m.churned} | {m.gross_adds} "
          f"| {m.net_adds} | {m.end_value} | {_money(m.spend)} |")
    a("")
    a("## Channel allocation (at peak demand)")
    a("")
    a("| Channel | Share | CAC | Gross adds/mo | Spend/mo | Leads/mo |")
    a("|---|---|---|---|---|---|")
    for c in plan.channels:
        a(f"| {c['name']} | {c['share']:.0%} | {_money(c['cac'])} "
          f"| {c['peak_monthly_gross_adds']} | {_money(c['peak_monthly_spend'])} "
          f"| {c['peak_monthly_leads_needed']} |")
    a("")
    a("## Feasibility")
    a("")
    for note in plan.feasibility_notes:
        a(f"- {note}")
    a("")
    a("## Strategic read")
    a("")
    a("- The 1,000-member target is a **step-change**, not an extrapolation: CRR "
      "currently adds roughly 200 clients/year (~17/month). The ramp above requires "
      "many times that, so the plan is fundamentally a marketing-spend and "
      "operational-capacity decision.")
    a("- **Capacity is the binding constraint.** Before spend scales, the dispute-"
      "processing workflow (currently 9-15 files/month) must be automated and/or "
      "staffed to absorb the new volume — see the automation roadmap.")
    a("- **Referral partnerships are the cheapest lever.** Mortgage brokers and prior "
      "affiliate sources convert far better than cold paid traffic; prioritize signing "
      "partners before scaling ad budget.")
    a("- Re-baseline this plan once the true current member count and monthly churn "
      "are confirmed from the billing system (open QoE diligence item).")
    return "\n".join(lines)


def main() -> None:
    plan = build_plan(
        metric_key="active_members",
        current_value=200,
        target_value=1000,
        start=date(2026, 6, 1),
        deadline=date(2026, 12, 31),
        monthly_churn_rate=0.05,
        capacity_per_month=30,
    )
    out_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "docs",
        "growth",
    )
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "crr-scaling-plan.md")
    with open(out_path, "w") as fh:
        fh.write(render(plan))
    print(f"Wrote {out_path}")
    print(
        f"  {plan.months} months, peak {plan.peak_monthly_gross_adds} adds/mo, "
        f"total spend ${plan.total_spend:,.0f}"
    )


if __name__ == "__main__":
    main()
