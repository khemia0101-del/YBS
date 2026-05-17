"""
Credit Repair Resources LLC — normalized financials for the baseline QoE.

Source: cash-basis P&Ls in the seller's Google Drive data room (PNL_2023.xlsx,
PNL_2024.xlsx, PNL_Jan_through_May_2025.xlsx). Statements are cash basis and show
no depreciation/amortization. Figures are entered exactly as reported; the addback
schedule reflects QoE judgment and is flagged for diligence confirmation.
"""
from __future__ import annotations

from app.services.qoe.engine import Addback, FinancialPeriod

COMPANY_NAME = "Credit Repair Resources LLC"

CRR_PERIODS: list[FinancialPeriod] = [
    FinancialPeriod(
        label="FY2023",
        revenue="316751.82",
        cogs="11595.64",
        operating_expenses="315395.59",
        interest="2145.35",
        net_income="-22924.27",
        months=12,
        notes="Elevated advertising ($24.9k) and payroll-processing fees ($18.3k) vs. FY2024.",
        addbacks=[
            Addback(
                label="Prior period adjustment",
                amount="10862.46",
                applies_to="ebitda",
                category="non_recurring",
                rationale="One-time prior-period correction booked to Other Expenses.",
                confidence="high",
            ),
            Addback(
                label="Related-party payment ('SydRae')",
                amount="36000.00",
                applies_to="sde",
                category="related_party",
                rationale="Recurring $36k/yr related-party payment; confirm nature in diligence.",
                confidence="medium",
            ),
            Addback(
                label="Interest expense",
                amount="2145.35",
                applies_to="sde",
                category="financing",
                rationale="Financing cost; buyer capital structure will differ.",
                confidence="high",
            ),
            Addback(
                label="Meals & entertainment (50%)",
                amount="1543.47",
                applies_to="sde",
                category="discretionary",
                rationale="Owner-discretionary portion of meals & entertainment.",
                confidence="medium",
            ),
        ],
    ),
    FinancialPeriod(
        label="FY2024",
        revenue="323083.07",
        cogs="8499.89",
        operating_expenses="310538.67",
        interest="3650.80",
        net_income="714.38",
        months=12,
        notes="Most recent full year — used as the valuation basis.",
        addbacks=[
            Addback(
                label="Related-party payment ('SydRae')",
                amount="36000.00",
                applies_to="sde",
                category="related_party",
                rationale="Recurring $36k/yr related-party payment; confirm nature in diligence.",
                confidence="medium",
            ),
            Addback(
                label="Officer life insurance",
                amount="4020.00",
                applies_to="sde",
                category="discretionary",
                rationale="Owner-benefit policy; not a cost the business requires.",
                confidence="high",
            ),
            Addback(
                label="Interest expense",
                amount="3650.80",
                applies_to="sde",
                category="financing",
                rationale="Financing cost; buyer capital structure will differ.",
                confidence="high",
            ),
            Addback(
                label="Meals & entertainment (50%)",
                amount="1796.67",
                applies_to="sde",
                category="discretionary",
                rationale="Owner-discretionary portion of meals & entertainment.",
                confidence="medium",
            ),
        ],
    ),
    FinancialPeriod(
        label="Jan-May 2025",
        revenue="128501.41",
        cogs="3309.09",
        operating_expenses="128926.19",
        interest="522.06",
        net_income="-4154.44",
        months=5,
        notes=(
            "Partial year. Contains bookkeeping artifacts (payroll-clearing -$7,985, "
            "unapplied cash bill payment $2,000) that warrant cleanup before relying on it."
        ),
        addbacks=[
            Addback(
                label="Related-party payment ('SydRae')",
                amount="20000.00",
                applies_to="sde",
                category="related_party",
                rationale="Five months of the recurring related-party payment.",
                confidence="medium",
            ),
            Addback(
                label="Interest expense",
                amount="522.06",
                applies_to="sde",
                category="financing",
                rationale="Financing cost.",
                confidence="high",
            ),
        ],
    ),
]

# Qualitative context drawn from the seller's pitch deck / data room.
CRR_CONTEXT = {
    "founded": 2007,
    "location": "Cleveland, Ohio",
    "staff": "3 full-time + 1 part-time",
    "owner_involvement": "3-5 hours/week",
    "revenue_model": (
        "$399 enrollment + $165/mo for 7 months (~$1,155/client), then $9.99/mo "
        "maintenance; plus affiliate commissions."
    ),
    "new_clients_per_year": "~200",
    "lifetime_clients": "10,000+",
}

VALUATION_RATIONALE = [
    "~97% gross margin and a recurring subscription model support the upper half of the range.",
    "Proprietary in-house dispute-management software is a transferable asset and a moat.",
    "Very low owner involvement (3-5 hrs/week) means the business is highly transferable.",
    "Small absolute SDE, flat revenue, and modest new-client acquisition cap the multiple.",
    "Single-owner, lifestyle-scale operation — buyer pool is individual operators, not strategics.",
]
