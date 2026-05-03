# ESOP Readiness — Normalized EBITDA, Add-Back Categories, Evidence Package

## LEGAL DISCLAIMER

**This software prepares evidence and calculations for professional review. It does NOT
replace an independent ESOP trustee, ERISA counsel, CPA, valuation firm, or tax advisor.
All outputs must be reviewed by qualified professionals before use in any ESOP transaction,
financing, or valuation. Do not treat any output as legal or tax advice.**

## Normalized EBITDA Bridge Formula

```
Book EBITDA (from QuickBooks P&L)
+ Owner discretionary expenses (documented, non-recurring post-close)
+ One-time transaction/diligence expenses
+ Non-operating expenses unrelated to core cleaning operations
+ Excess owner compensation above market replacement cost (if supportable)
- Missing market costs not currently recorded
- Under-accrued payroll taxes, workers comp, insurance, or benefits
- Non-recurring revenue not expected to continue
- One-time project revenue unrelated to recurring contracts
= Normalized EBITDA
```

## Add-Back Categories (Positive Adjustments)

Each add-back MUST have:
- `evidence_id` linking to source QB entry or document
- `description` explaining why it is non-recurring or owner-specific
- `reviewer_status` = 'approved' before inclusion in any package
- `requires_approval` = true (cannot be self-approved by agent)

| Category | Allowed if | Evidence required |
|---|---|---|
| `owner_discretionary` | Clearly personal or owner-specific, not needed post-close | Transaction detail, vendor, written explanation |
| `one_time_expense` | Not recurring, not needed to operate | Invoice, date, non-recurring proof |
| `related_party_rent` | Above or below market, adjustable post-close | Lease agreement, market benchmark, proposed adjustment |
| `excess_owner_comp` | Owner comp exceeds market replacement cost | Payroll records, role description, market comp support |
| `transaction_costs` | Related to sale/acquisition/ESOP setup, not ordinary ops | Invoice and project description |
| `non_operating_asset` | Not needed for cleaning/facility operations | Asset list, expense detail, disposition plan |

## Negative Adjustments (Must Not Be Skipped)

A credible QoE report includes BOTH add-backs AND negative adjustments.
Skipping negative adjustments will cause a trustee or valuation firm to distrust the report.

| Negative item | Example |
|---|---|
| Missing owner labor post-close | Owner performing unpaid work that will need to be replaced |
| Under-accrued payroll burden | Workers comp, FICA, SUTA not fully expensed |
| Unrecorded insurance costs | Insurance renewals not yet posted |
| Bad debt reserve | AR > 90 days with no collection history |
| One-time revenue | Unusual project revenue not expected to recur |
| Below-market management fee | Owner receiving below-market management fee (gap = future cost) |

## ESOP Readiness Score

```
ESOP_Readiness_Score = weighted_average(
  financial_statement_cleanliness     * 0.15,
  source_evidence_coverage            * 0.15,
  addback_defensibility               * 0.15,
  recurring_revenue_quality           * 0.15,
  customer_concentration_risk_inverse * 0.10,
  compliance_document_completeness    * 0.10,
  payroll_and_labor_traceability      * 0.10,
  cash_forecast_reliability           * 0.05,
  audit_trail_completeness            * 0.05
)

Score interpretation:
  0.85–1.00: Strong — suitable for diligence package
  0.70–0.84: Moderate — address flagged gaps before submission
  0.50–0.69: Weak — significant work needed
  < 0.50: Not ready — do not submit to trustee or lender
```

## Valuation Evidence Package Contents

A complete package contains:
1. Normalized EBITDA bridge (book → adjusted, with waterfall)
2. Revenue quality report (recurring vs. one-time, by customer/contract)
3. Expense quality report (operating vs. non-operating, owner vs. market)
4. Customer concentration analysis
5. AR aging report and DSO trend
6. Working capital analysis
7. Contract profitability schedule
8. Compliance evidence summary (insurance, certs, licenses)
9. Unresolved exceptions log (transparency on data gaps)
10. Disclaimer page (legal/tax/fiduciary disclaimer, always present)

## What the Package Must NOT Do

- Make any legal conclusion about ESOP eligibility.
- State that the company qualifies for Section 1042 or S-corp ESOP tax treatment.
- Represent a final valuation or appraised value.
- Substitute for an independent trustee's feasibility analysis.
- Include raw credentials, private emails, or unrelated personal information.

## C-Corp Section 1042 and S-Corp ESOP Notes (Informational Only)

The system may model scenario outputs related to these structures as labeled SCENARIOS.
These outputs must be labeled: "FOR PLANNING DISCUSSION ONLY — NOT TAX ADVICE."
Professional review by CPA and ERISA counsel is required before any transaction structuring.
