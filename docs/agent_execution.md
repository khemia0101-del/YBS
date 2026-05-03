# Agent Execution — Task States, Permission Model, and Failure Handling

## Task State Machine

```
QUEUED
  └─► RUNNING
        ├─► COMPLETED (success)
        ├─► AWAITING_APPROVAL (high-risk action detected)
        │     ├─► APPROVED ──► RUNNING (resumed)
        │     └─► REJECTED ──► FAILED
        └─► FAILED
              ├─► QUEUED (retry_count < max_retries, exponential backoff)
              └─► TERMINAL_FAILED (retry_count >= max_retries)
                    └─► notification sent to operator
```

## Permission Model

Agents are identified by `agent_id` (e.g., "hermes", "openclaw", "system").
All agent actions are logged in `agent_action_logs` before AND after execution.

| Risk level | Permission | Trigger condition |
|---|---|---|
| LOW | AUTO — no approval needed | Document request, AR reminder (template-approved), internal exception summary |
| MEDIUM | APPROVAL_REQUIRED — analyst | Scope clarification draft, external compliance doc request |
| HIGH | APPROVAL_REQUIRED — admin | Repricing email, renegotiation, ESOP package send |
| CRITICAL | APPROVAL_REQUIRED — admin + MFA | Termination notice, legal demand, trustee/lender submission |
| BLOCKED | Never executes in MVP | Any money movement, direct financial table writes |

## Prohibited Table Writes for Agent Actors

The `complete_task` function validates `tables_written` before committing.
If an agent attempts to write to any of these tables, `AgentGuardrailViolation` is raised:

```python
AGENT_WRITE_PROHIBITED = {
    "customers", "contracts", "sites", "invoices", "payments",
    "labor_shifts", "subcontractors", "supervisors",
    "profitability_runs", "profitability_run_lines",
    "dso_snapshots", "cash_forecast_runs", "cash_forecast_weeks",
    "qoe_runs", "esop_adjustments", "decisions",
}
```

## Agent Action Log Requirements

Every agent action MUST log:
- `task_id`: UUID of the `agent_tasks` record
- `agent_id`: string identifier ("hermes", "openclaw")
- `action_type`: what was done ("read_staged_records", "create_approval_request", etc.)
- `input_snapshot`: JSONB of inputs (sanitized — no credentials)
- `output_snapshot`: JSONB of outputs
- `tables_read`: list of tables accessed for reading
- `tables_written`: list of tables written (validated against prohibition list)
- `was_approved`: whether human approval was obtained
- `created_at`: immutable timestamp

`agent_action_logs` is append-only. No UPDATE or DELETE is permitted.

## Approval Request Lifecycle

1. Agent detects high-risk action needed.
2. Agent creates `approval_requests` record with `status='pending'`.
3. Agent sets `agent_tasks.status = 'awaiting_approval'`.
4. Notification sent to operator (Telegram/email).
5. Operator reviews in Agent Ops screen.
6. If APPROVED: `approval_requests.status = 'approved'`, task resumes.
7. If REJECTED: `approval_requests.status = 'rejected'`, task set to `failed`.
8. If no response in 48 hours: escalate to admin, reset expiry.

## Communication Template Rules

- Agents MUST use approved templates from `communication_templates` table.
- No free-form external messages without template selection.
- Template variables are populated from verified DB records only.
- LLM-generated text may be used for INTERNAL draft summaries only, not external sends.
- Every send is logged with: template_id, template_version, recipient, evidence_ids_used.

## Failure Handling

| Failure type | System response |
|---|---|
| Integration sync fails | Create exception in staged_records, retry with exponential backoff (2s, 4s, 8s, 16s), notify operator after 3 failures |
| Agent tool call fails | Mark task FAILED, capture error in agent_action_logs, retry if retry_count < max_retries |
| Low confidence extraction | Keep staged with status='pending', create exception, block downstream calculations |
| Conflicting source data | Show conflict in exception queue with source hierarchy; do NOT silently overwrite |
| Agent attempts prohibited write | Raise AgentGuardrailViolation, log security incident to audit_logs, notify admin |
| Approval request expires (48h) | Re-escalate with new approval_request, keep task in awaiting_approval |
| Financial calculation changes after correction | Recalculate dependent metrics as Celery tasks, mark prior run 'superseded' |

## Hermes Daily Loop Implementation

```python
async def hermes_daily_loop():
    async with get_session() as session:
        # Step 1: Check sync results
        sync_results = await get_overnight_sync_status(session)

        # Step 2: Summarize exceptions
        exceptions = await get_pending_exceptions(session, limit=50)

        # Step 3: Cash and AR risks
        cash_breaches = await get_cash_forecast_breaches(session)
        ar_risks = await get_overdue_invoices(session, days_threshold=30)

        # Step 4: Auto-execute low-risk tasks
        for task in await get_auto_executable_tasks(session):
            await execute_task(session, task)

        # Step 5: Draft high-risk actions
        for task in await get_draft_needed_tasks(session):
            await draft_and_request_approval(session, task)

        # Step 6: Notify operator
        await send_operator_summary(session, {
            "sync_results": sync_results,
            "exceptions": exceptions,
            "cash_breaches": cash_breaches,
            "ar_risks": ar_risks,
        })
```
