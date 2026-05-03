# Acceptance Criteria — Per-Phase Pass Conditions

A phase is NOT complete until ALL criteria in that phase pass.

## Phase 1: Foundation

- [ ] `make migrate` runs cleanly on a fresh database with no errors
- [ ] `GET /health` returns 200 with `{"status": "ok", "db": "ok", "redis": "ok"}`
- [ ] `POST /api/v1/ingestion/upload` creates a `raw_records` row with correct SHA-256 checksum
- [ ] Re-uploading the same file marks the second record as `is_duplicate=True`
- [ ] Every state-changing API call creates exactly 1 row in `audit_logs`
- [ ] `AGENTS.md` exists at repo root and contains all 10 hard rules

## Phase 2: Integrations

- [ ] CSV upload (bank CSV) successfully ingests to `raw_records` with source_system='bank_csv'
- [ ] Payroll CSV upload ingests to `raw_records` with source_system='payroll'
- [ ] QuickBooks OAuth callback endpoint returns 200 and stores encrypted tokens
- [ ] Sync log created for every sync attempt (success or failure)
- [ ] Duplicate raw records rejected by checksum constraint

## Phase 3: Reconciliation UI

- [ ] `GET /api/v1/staging/exceptions` returns paginated list with all required fields
- [ ] Exception with confidence >= 0.92 is auto-approved (status='auto_approved')
- [ ] Exception with confidence < 0.70 stays in exception queue (status='pending')
- [ ] `POST /staging/exceptions/{id}/approve` transitions status and writes audit log
- [ ] Frontend Exception Queue renders all pending exceptions
- [ ] Bulk approve of 5 exceptions creates 5 audit log entries
- [ ] Stats endpoint returns correct counts by status

## Phase 4: Financial Truth

- [ ] `run_company_profitability()` succeeds with approved staged data
- [ ] All `profitability_run_lines` have `evidence_id` and `confidence_score`
- [ ] `profitability_run_lines` without `evidence_id` raise validation error
- [ ] DSO calculation matches hand-verified result for known dataset
- [ ] Scope creep index > 1.10 creates a `decisions` record with type='reprice'
- [ ] Customer > 20% revenue creates concentration_warning flag

## Phase 5: Cash / Decision

- [ ] 13-week forecast has exactly 13 rows in `cash_forecast_weeks`
- [ ] `SUM(net_cash_flow)` = ending_cash - beginning_cash for the run
- [ ] Stress test with customer removal produces different ending_cash than baseline
- [ ] Bid score returning negative margin produces decision with label='BLOCKED'
- [ ] Customer concentration breach produces decision with label='APPROVAL_REQUIRED'

## Phase 6: ESOP Optimization

- [ ] EBITDA bridge: `adjusted_ebitda = reported_ebitda + total_addbacks - total_negative_adj`
- [ ] Agent cannot self-approve esop_adjustments (requires_approval must be True)
- [ ] Valuation package export contains disclaimer text on every page
- [ ] Package export does NOT contain raw credentials or private emails
- [ ] All add-backs in exported package have `reviewer_status='approved'`

## Phase 7: Agent Layer

- [ ] Agent attempting to write to `profitability_runs` raises `AgentGuardrailViolation`
- [ ] Task state machine: invalid transition raises error, valid transitions succeed
- [ ] LOW risk task executes without approval
- [ ] HIGH risk task creates approval_request and pauses at AWAITING_APPROVAL
- [ ] Approval_request approved by admin → task resumes to RUNNING
- [ ] All agent actions appear in `agent_action_logs`
- [ ] Telegram notification enqueued when exception count exceeds threshold

## Phase 8: Hardening

- [ ] Viewer role: `POST /approvals/{id}/approve` returns 403
- [ ] Agent service account: write to `invoices` returns 403
- [ ] Bandit security scan: no HIGH severity findings
- [ ] SQL injection test: malicious customer name filter does not execute raw SQL
- [ ] `POST /auth/login` rate-limited to 10 requests/minute (429 after)
- [ ] `DELETE` on `audit_logs` returns error (PG row-level security)
- [ ] All QB OAuth tokens encrypted at rest (not plaintext in DB)
- [ ] `make test` runs all tests and passes with >= 80% coverage
