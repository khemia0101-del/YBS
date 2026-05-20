# YBS OS

An AI-native operations platform for running small businesses — built first
for the **Credit Repair Resources LLC (CRR)** acquisition, but designed as a
generic, multi-business system that adapts to any business from that
business's own inputs. Internal tool. No billing.

> **Status:** Phases 0–8 are merged to `main`. Phases 9–12 (AI COO + the
> self-improving AI-native overlay) are committed and pushed on
> `claude/credit-repair-integration-Ttxf5`, awaiting a merge.

---

## Why this exists

We're consolidating operations on top of a single platform that:

1. **Reconstructs financial truth** for any acquired business (QoE, valuation,
   cash, profitability) directly from its raw sources.
2. **Runs day-to-day operations** through an AI executive layer the owner
   talks to like a COO — propose-then-approve on every outbound action.
3. **Improves itself.** Sensors record everything into a company brain;
   continuous loops act through a policy/quality gate; a monitor agent
   watches the system and drafts its own fixes.

The model: **burn tokens, not headcount.** ICs supervise; the platform does
the rest, on a tight propose-then-approve leash.

---

## Architecture

Five layers, mapped to the YC self-improving-company pattern:

| Layer | What it is | In this repo |
|---|---|---|
| **Sensors** | Record everything | `services/integrations/` (Plaid, QuickBooks, Gmail), `services/knowledge/` (company brain), Drive MCP |
| **Policy** | What can act alone vs. needs approval | `services/agents/task_queue.py`, `security/rbac.py`, `AGENT_WRITE_PROHIBITED` guardrail |
| **Tools** | Deterministic APIs the AI can call | `services/financial/`, `services/cash/`, `services/qoe/`, `services/growth/`, `services/coo/actions.py` |
| **Quality gate** | Human-in-the-loop approval + audit | `models/agent.py::ApprovalRequest`, `AgentActionLog`, `CooAction` propose-then-approve |
| **Learning** | Monitor + draft fixes + continuous loops | `services/monitor/`, `services/ops_loops/` |

Stack: **FastAPI + SQLAlchemy/Postgres + Redis + Celery + React + Anthropic
(Claude) + Voyage AI embeddings**. Tenant-scoped: a `Tenant` owns one or
more `Company` records; every business row is filtered by `tenant_id`.

---

## What's built

### On `main` (merged, Phases 0–8)

- **Phase 0 — Multi-tenancy.** `Tenant` ↔ `Company`, JWT-scoped users,
  enforced row filtering across every router, two-tenant isolation tests.
- **Phase 1 — Adaptive business profile.** `BusinessProfile`,
  `MetricDefinition`, `MetricSnapshot`. Engines read profile config rather
  than hard-coding any vertical.
- **Phase 2 — Integrations.** Plaid + QuickBooks + Gmail connectors, OAuth
  scaffolding, encrypted credential vault, Celery beat sync.
- **Phase 3 — QoE engine + CRR baseline.** Drive document ingest,
  EBITDA→SDE bridge, valuation, written CRR report at
  `docs/qoe/crr-baseline-report.md`.
- **Phase 4 — Configurable KPI metrics.** Computes whatever the profile
  declares; daily snapshots for trend tracking.
- **Phase 5 — AI conversational interviewer.** Adaptive owner/employee
  interview that doubles as onboarding discovery and operations mapping.
- **Phase 6 — Automation roadmap.** Ranks effort/impact-scored automations;
  actionable items become approval-gated `AgentTask`s.
- **Phase 7 — Growth/scaling model.** Generic; CRR config tracks the path to
  1,000 members by 2026-12-31. Strategy at `docs/growth/crr-scaling-plan.md`.
- **Phase 8 — Profitability recommendations.** Ranked, dollar-quantified
  ideas with rationale; trackable over time.

### On `claude/credit-repair-integration-Ttxf5` (awaiting merge, Phases 9–12)

- **Phase 9 — AI Executive Assistant ("AI COO").** Conversational COO with
  live KPI/QoE/automation/profit context. Every outbound action — employee
  email, in-app task, business change — is a `CooAction` the owner approves
  with one tap. SendGrid for email, in-app `EmployeeTask`s for assignments.
- **Phase 10 — Company brain (RAG).** Tenant-scoped `KnowledgeDocument` +
  `KnowledgeChunk` over Gmail bodies, interview threads, QoE runs, profit
  recommendations, metric trends, agent actions, and uploaded meeting
  transcripts (txt/vtt/srt/json). Voyage AI embeddings when
  `VOYAGE_API_KEY` is set; keyword-overlap fallback otherwise. The AI COO
  retrieves top-k chunks alongside its briefing.
- **Phase 11 — Self-improving monitor agent.** Hourly Celery loop runs four
  collectors (terminal `AgentTask` failures, recurring `ApprovalRequest`
  rejection clusters, `MetricSnapshot` >2σ anomalies, failed `CooAction`s),
  each producing an `AgentObservation`. Claude + the company brain draft a
  `MonitorDiagnosis` containing a unified-diff patch and rationale; a
  reviewer agent critiques it. Owner approves each one — no auto-deploy in
  this round. With `GITHUB_TOKEN` set, approval opens a draft PR.
- **Phase 12 — Continuous ops loops.** `OpsLoop`s are cron-scheduled agents
  that re-analyze the business and queue `CooAction`s through the existing
  approval flow. A 5-minute Celery dispatcher uses `croniter` to fire any
  due loop. Seeds two CRR loops: weekly metrics+funnel review and daily
  cash-health watch.

---

## What's next

Deferred from the AI-native overlay round; pick up when capacity allows:

- **Direct meeting-recording integrations.** Today: upload a transcript
  file. Next: Zoom/Otter/Granola pulls + Whisper transcription so raw audio
  becomes a brain document automatically.
- **Slack / Teams ingestion.** Feed DMs and channels into the company brain.
- **Customer-support ticket ingestion** (Intercom / Zendesk / HelpScout).
- **AI-CPO ship-overnight.** Customer suggestion → triage → if aligned,
  drafted code change → reviewer agent → human one-tap → deploy.
- **Auto-deploy monitor.** Promote specific low-risk diagnosis types from
  "human approves" to "AI-reviews + ships overnight."
- **Ephemeral one-shot UIs.** Generate internal tool screens from prompts
  on demand instead of hand-coding every page.
- **Token-maxing dashboard.** Per-user/per-feature Anthropic + Voyage token
  usage so we can see who and what is leveraging the platform.
- **Frontend pages for Phases 9–12.** The backend ships first; we'll surface
  the COO chat, monitor tray, ops-loop CRUD, and knowledge search in the UI
  next.

---

## Running it

```bash
# One-time
cp .env.example .env       # fill in keys (see below)
make up                    # docker compose: postgres, redis, backend, frontend, worker, beat
make migrate               # alembic upgrade head
make seed                  # 2 tenants, CRR + YBS + Acme; CRR ops-loops + QoE seeded
make test                  # pytest

# Day-to-day
make backend-dev           # uvicorn with reload
make frontend-dev          # vite dev server
make worker                # celery worker
make beat                  # celery beat (cron dispatcher)
```

### Required environment variables

Minimum to boot:

- `SECRET_KEY`, `ENCRYPTION_KEY`, `DATABASE_URL`, `REDIS_URL`

For AI features:

- `ANTHROPIC_API_KEY` — Claude (interviewer, COO, monitor, ops loops)

For data ingestion (each needs OAuth completed once in a browser):

- `PLAID_CLIENT_ID`, `PLAID_SECRET`
- `QB_CLIENT_ID`, `QB_CLIENT_SECRET`, `QB_REDIRECT_URI`
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`

For the AI COO to email employees:

- `SENDGRID_API_KEY`, `NOTIFICATIONS_FROM_EMAIL`

Optional (Phase 10–11):

- `VOYAGE_API_KEY`, `VOYAGE_MODEL` — embeddings for the company brain.
  Without them, retrieval falls back to keyword search.
- `GITHUB_TOKEN`, `GITHUB_REPO` — let the monitor open draft PRs when a
  diagnosis is approved.

See `.env.example` for the complete list.

---

## Repo layout

```
backend/
  app/
    models/         # SQLAlchemy models
    routers/        # FastAPI routers (mounted under /api/v1/*)
    services/       # business logic — financial/, qoe/, growth/, coo/,
                    # knowledge/, monitor/, ops_loops/, agents/, ...
    workers/        # Celery tasks + beat schedule
    security/       # auth, RBAC, tenant isolation, credential vault
    schemas/        # Pydantic request/response models
  alembic/          # one migration per schema-changing phase
  tests/            # pytest unit + acceptance
  scripts/          # seed_dev_data.py
frontend/           # React + Vite (in progress for Phases 9–12)
docs/
  qoe/crr-baseline-report.md
  growth/crr-scaling-plan.md
```

---

## Branching

- **`main`** — production-ready. Each merged PR represents a completed
  phase.
- **`claude/credit-repair-integration-Ttxf5`** — current working branch.
  Phases 9–12 sit here awaiting merge.
- Feature work happens on `claude/*` branches and lands via PR with passing
  tests.

Default tests must stay green; the `test_fuzzy_match` parametrization
edge case and four `test_dso_engine` SQLite-typing errors pre-date this
work and are tracked separately — they don't gate the new phases.

---

## Tenancy + security

- Every business row has a `tenant_id`; every router resolves the caller's
  tenant from the JWT and filters by it. Cross-tenant reads are blocked
  (see `backend/tests/unit/test_tenant_isolation.py`).
- The AI **proposes**; humans **approve**. The AI never writes to business
  tables directly — the `AGENT_WRITE_PROHIBITED` guardrail in
  `services/agents/` enforces this.
- Every AI action is audited in `AgentActionLog` (immutable, append-only).
- API credentials are encrypted at rest in `IntegrationCredential` via the
  `CredentialVault`.

---

## Questions / how to plug in

- **Where does my business get added?** New tenant + company through admin
  onboarding (`/api/v1/admin/*`). The AI interviewer infers an initial
  `BusinessProfile` you confirm/edit.
- **How do I see what the platform thinks?** `/api/v1/coo/` is the chat
  endpoint; `/api/v1/coo/actions` is the approval tray; `/api/v1/monitor/`
  surfaces observations + diagnoses; `/api/v1/ops-loops/` lists continuous
  loops.
- **How do I extend it to a new business vertical?** Add the right metrics
  to that company's `BusinessProfile`; the engines pick them up. No code
  change needed for a new vertical.

If anything in this README drifts from reality, fix it — this file is the
team's source of truth for what's actually built.
