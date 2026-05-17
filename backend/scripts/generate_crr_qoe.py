#!/usr/bin/env python3
"""
Generate the Credit Repair Resources baseline QoE report.

Writes docs/qoe/crr-baseline-report.md from the engine + CRR data-room figures.

Usage:
    cd backend && python scripts/generate_crr_qoe.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.qoe.crr_data import (  # noqa: E402
    COMPANY_NAME,
    CRR_CONTEXT,
    CRR_PERIODS,
    VALUATION_RATIONALE,
)
from app.services.qoe.engine import analyze  # noqa: E402
from app.services.qoe.report import render_markdown  # noqa: E402
from app.services.qoe.valuation import value_by_sde  # noqa: E402

OBSERVATIONS = [
    "Revenue is essentially flat: FY2023 $316.8k -> FY2024 $323.1k (+2.0%); Jan-May 2025 "
    "annualizes to ~$308k. The business is stable but not growing on its own.",
    "Gross margin is exceptionally high (~97%) and consistent — a genuinely asset-light, "
    "software-leveraged service model.",
    "Reported profitability is razor-thin: FY2024 net income was just $714 and operating "
    "income $4,045. The owner's economic return shows up as SDE, not net income.",
    "~3.5% of FY2024 revenue is affiliate commission income ($11.3k) — a second, "
    "lower-effort revenue stream.",
    "FY2023 was distorted by elevated advertising ($24.9k vs. $5.5k in FY2024), elevated "
    "payroll-processing fees ($18.3k vs. $1.4k), and a $10.9k prior-period adjustment — "
    "FY2024 is the cleaner valuation basis.",
    "The recurring 'SydRae' payment ($36k/yr) is the single largest discretionary item "
    "and the biggest swing factor in SDE — its treatment must be confirmed.",
]

DILIGENCE = [
    "Confirm the nature of the 'SydRae' $36k/yr payment (owner draw, family member on "
    "payroll, or genuine vendor) and whether it is a true addback.",
    "Obtain the wage ledger by employee to isolate any owner compensation inside the "
    "$154k FY2024 wages line — a likely further SDE addback.",
    "Reconcile active-member count and MRR to the billing system; the current count "
    "drives both valuation and the 1,000-member growth plan.",
    "Verify FY2024 figures against the 2024 tax return and bank statements.",
    "Clean up the 2025 ledger (payroll-clearing and unapplied-cash entries) and obtain a "
    "normalized YTD P&L.",
    "Quantify customer/referral concentration — revenue per referral source.",
]


def main() -> None:
    qoe = analyze(CRR_PERIODS, primary_label="FY2024")
    valuation = value_by_sde(
        qoe.primary.sde, 2.0, 2.75, 3.5, rationale=VALUATION_RATIONALE
    )
    markdown = render_markdown(
        COMPANY_NAME,
        qoe,
        valuation,
        CRR_PERIODS,
        context=CRR_CONTEXT,
        observations=OBSERVATIONS,
        diligence_flags=DILIGENCE,
    )
    out_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "docs",
        "qoe",
    )
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "crr-baseline-report.md")
    with open(out_path, "w") as fh:
        fh.write(markdown)
    print(f"Wrote {out_path}")
    print(f"  FY2024 SDE: ${qoe.primary.sde:,.2f}")
    print(
        f"  Valuation range: ${valuation.low_value:,.0f} - "
        f"${valuation.high_value:,.0f} (mid ${valuation.mid_value:,.0f})"
    )


if __name__ == "__main__":
    main()
