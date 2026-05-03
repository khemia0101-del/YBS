# AGENTS.md — YBS OS

You are a coding agent working on YBS OS: a financial truth reconstruction, operating control,
and ESOP-readiness platform for acquisition underwriting of Young Building Solutions, a
commercial janitorial/cleaning services company.

## Business Objective

- Reconstruct financial truth from raw QuickBooks, bank, payroll, and scheduling data.
- Optimize legitimate reported earnings and ESOP-readiness evidence.
- Build controlled agent execution with human approval for high-risk actions.
- Support acquisition diligence and eventual ESOP transition.

## Schema Ownership

| Model file | Owner | Description |
|---|---|---|
| `app/models/base.py` | Schema/Data Agent | TimestampMixin, AuditMixin, Base |
| `app/models/core.py` | Schema/Data Agent | companies, customers, contracts, sites |
| `app/models/transactions.py` | Schema/Data Agent | invoices, payments, labor_shifts, subcontractors |
| `app/models/raw.py` | Schema/Data Agent | raw_records, staged_records |
| `app/models/financial.py` | Schema/Data Agent | profitability_runs, dso_snapshots, cash_forecast_runs |
| `app/models/esop.py` | QoE/ESOP Agent | esop_adjustments, qoe_runs, valuation_evidence_files |
| `app/models/agent.py` | Agent Execution Agent | agent_tasks, agent_action_logs, approval_requests |

## Hard Rules

1. **Do not invent schemas.** Use canonical Alembic migrations in `alembic/versions/`. Never create ad-hoc tables.
2. **Never write LLM outputs directly to normalized financial tables.** All AI extractions go to `staged_records` first.
3. **Every financial metric requires:** `evidence_id`, `confidence_score`, `calculation_version`.
4. **Uncertainty creates exceptions, not fake precision.** When confidence < 0.70, create a staged exception.
5. **Hermes executes only approved tasks.** Task status must be `approved` before execution.
6. **OpenClaw is an execution adapter, not the rules engine.** Financial logic lives in `app/services/financial/`.
7. **High-risk external actions require human approval.** Repricing, termination, ESOP export = APPROVAL_REQUIRED.
8. **No money movement in MVP.** Block any task attempting payment initiation.
9. **ESOP outputs are evidence packages, not legal/tax advice.** Disclaimer required on all exports.
10. **Build truth first, decisions second, execution third.**

## Prohibited Agent Writes

Agents (actor_type='agent') may NEVER write to these tables:
- `customers`, `contracts`, `sites`, `invoices`, `payments`
- `labor_shifts`, `subcontractors`, `supervisors`
- `profitability_runs`, `profitability_run_lines`
- `dso_snapshots`, `cash_forecast_runs`, `qoe_runs`
- `esop_adjustments`, `decisions`

Agents MAY write to:
- `raw_records`, `staged_records`, `exceptions`
- `agent_tasks`, `agent_action_logs`, `approval_requests`
- `rule_change_proposals`, `agent_memory_exports`

## Approval Thresholds

| Risk level | Required approver | Examples |
|---|---|---|
| LOW | Auto (no human needed) | Document request, AR reminder (template-approved), internal summary |
| MEDIUM | Analyst role | Scope clarification draft, external document request |
| HIGH | Admin role | Repricing email, contract renegotiation, ESOP package export |
| CRITICAL | Admin + MFA | Contract termination, legal demand, valuation to trustee |

## Required Fields for All AI Outputs

Any record produced by an AI/LLM extraction MUST include:
- `evidence_id` — UUID of the source `raw_record`
- `confidence_score` — float 0.0–1.0
- `calculation_version` — string e.g. "v1.0.0"

## Before Making Any Change

1. Read this file.
2. Check the canonical schema in `alembic/versions/`.
3. Do not create a second schema because the canonical one is inconvenient.
4. Check `docs/financial_truth.md` before writing any financial calculation.
5. Check `docs/agent_execution.md` before writing any agent or task logic.
