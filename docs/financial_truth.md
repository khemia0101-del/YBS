# Financial Truth — Formulas, Source Hierarchy, and Confidence Rules

## Core Principle

Every financial metric must have: `evidence_id`, `confidence_score`, `calculation_version`.
No metric is written to normalized tables without these three fields populated.
When data is uncertain, create an exception — not a fake answer.

## Source Hierarchy (highest to lowest trust)

1. **QuickBooks verified invoice** — matched to bank payment
2. **QuickBooks invoice** — unmatched but QB-confirmed
3. **Bank statement transaction** — matched to QB record
4. **Bank statement transaction** — unmatched
5. **Payroll export (ADP/Gusto/Paychex)** — provider-confirmed
6. **Swept shift data** — matched to site and payroll
7. **Manual entry by operator** — reviewed and approved
8. **AI extraction from document** — staged, pending review
9. **AI extraction, low confidence** — exception queue, blocked from downstream

## Contribution Margin Formula

```
revenue                = SUM(invoices.amount WHERE contract_id AND period)
direct_labor_w2        = SUM(labor_shifts.labor_cost WHERE worker_type='W2' AND contract_id AND period)
direct_labor_sub       = SUM(labor_shifts.labor_cost WHERE worker_type='SUB' AND contract_id AND period)
labor_burden_pct       = fica_rate + workers_comp_rate + unemployment_rate + benefits_pct + training_pct
burdened_labor_w2      = direct_labor_w2 * (1 + labor_burden_pct)
total_direct_labor     = burdened_labor_w2 + direct_labor_sub
supplies_cost          = direct assignment from QB expense categories
supervision_alloc      = supervisor_cost * (contract_revenue / total_revenue_in_supervisor_zone)
contribution_margin    = revenue - total_direct_labor - supplies_cost
gross_profit           = contribution_margin - overhead_alloc - supervision_alloc
gross_margin_pct       = gross_profit / revenue
```

## Days Sales Outstanding (DSO)

```
DSO = (total_accounts_receivable / revenue_in_period) * days_in_period

AR Aging Buckets:
  0-30 days:  invoices where (today - invoice_date) BETWEEN 0 AND 30
  31-60 days: invoices where (today - invoice_date) BETWEEN 31 AND 60
  61-90 days: invoices where (today - invoice_date) BETWEEN 61 AND 90
  91+ days:   invoices where (today - invoice_date) > 90
```

## Scope Creep Index

```
scope_creep_index = actual_labor_hours / contracted_labor_hours

Thresholds:
  > 1.10 = reprice_review trigger (decision created)
  > 1.20 = urgent reprice (APPROVAL_REQUIRED decision)
  > 1.35 = margin destruction alert (HIGH priority exception)
```

## Customer Concentration Risk

```
customer_concentration_pct = customer_revenue / total_company_revenue

Thresholds:
  > 20%: concentration_warning flag on customer record
  > 25%: bids for this customer require APPROVAL_REQUIRED
  > 40%: RED flag, blocks new bids without admin override
```

## Labor Burden Defaults (overridable per company via admin settings)

```
fica_employer_pct     = 0.0765   # 6.2% SS + 1.45% Medicare
futa_pct              = 0.006    # 0.6% after state credit
suta_pct              = 0.027    # varies by state, use 2.7% default
workers_comp_pct      = 0.035    # varies by job class, use 3.5% default
benefits_pct          = 0.0      # 0% if no benefits offered
training_pct          = 0.005    # 0.5% estimated training cost
total_burden_pct      = sum of above ≈ 0.1535 (15.35%)
```

## Confidence Scoring

```
confidence_score = weighted_average(
  source_reliability_score   * 0.40,
  completeness_score         * 0.30,
  match_corroboration_score  * 0.20,
  consistency_score          * 0.10
)

Thresholds:
  >= 0.92: auto_approve (AGENT_CONFIDENCE_AUTO_APPROVE env var)
  0.70–0.91: needs_review — goes to exception queue
  < 0.70: blocked — cannot flow to downstream calculations
```

## Calculation Versioning

Every `profitability_run`, `dso_snapshot`, `cash_forecast_run`, and `qoe_run` stores:
- `calculation_version`: semver string ("v1.0.0")
- `evidence_bundle`: JSONB with source record IDs used

When a formula changes, increment `calculation_version`. Prior runs are NOT deleted —
they are marked `status='superseded'`. This preserves the audit trail for ESOP diligence.

## What Triggers a Recalculation

- A staged_record is approved that affects a contract's invoices, payments, or labor.
- Labor burden assumptions are updated.
- A manual_override is applied or revoked.
- QuickBooks sync brings in amended records.

Recalculation is ALWAYS asynchronous (Celery task). The prior run stays `approved`
until the new run is also approved by an operator.
