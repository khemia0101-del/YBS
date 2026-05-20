"""Self-improving monitor (Phase 11) — collectors, diagnose, reviewer."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.agent import AgentTask, ApprovalRequest
from app.models.business import MetricDefinition, MetricSnapshot
from app.models.coo import CooAction
from app.models.monitor import AgentObservation, MonitorDiagnosis
from app.services.monitor import github
from app.services.monitor.agent import diagnose
from app.services.monitor.collectors import (
    collect_agent_task_failures,
    collect_approval_rejection_clusters,
    collect_coo_action_failures,
    collect_metric_anomalies,
    run_all_collectors,
)
from app.services.monitor.reviewer import review


@pytest.mark.asyncio
async def test_collect_agent_task_failures(db_session, sample_company):
    db_session.add(
        AgentTask(
            id=uuid.uuid4(),
            company_id=sample_company.id,
            task_type="sync_quickbooks",
            status="terminal_failed",
            error_message="403 unauthorized",
            retry_count=3,
        )
    )
    await db_session.flush()
    out = await collect_agent_task_failures(db_session)
    assert len(out) == 1
    assert out[0].source_type == "agent_task_failure"
    # Idempotent on a second run.
    out2 = await collect_agent_task_failures(db_session)
    assert out2 == []


@pytest.mark.asyncio
async def test_collect_approval_rejection_clusters(db_session, sample_company):
    for _ in range(4):
        db_session.add(
            ApprovalRequest(
                id=uuid.uuid4(),
                company_id=sample_company.id,
                requested_by="hermes",
                action_description="auto-write off invoice over $5k",
                status="rejected",
                required_role="admin",
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            )
        )
    await db_session.flush()
    out = await collect_approval_rejection_clusters(db_session, threshold=3)
    assert len(out) == 1
    assert "Repeated rejections" in out[0].title


@pytest.mark.asyncio
async def test_collect_metric_anomalies(db_session, sample_company):
    metric = MetricDefinition(
        id=uuid.uuid4(),
        company_id=sample_company.id,
        key="active_members",
        name="Active members",
        unit="count",
        category="growth",
        is_north_star=True,
    )
    db_session.add(metric)
    await db_session.flush()
    # Stable history then a sudden plunge.
    for i, value in enumerate([100, 102, 99, 101, 103, 100, 102, 30]):
        db_session.add(
            MetricSnapshot(
                id=uuid.uuid4(),
                company_id=sample_company.id,
                metric_definition_id=metric.id,
                period_date=date(2026, 1, 1) + timedelta(days=i * 7),
                period_type="weekly",
                value=Decimal(value),
                source="computed",
            )
        )
    await db_session.flush()
    out = await collect_metric_anomalies(db_session, z_threshold=2.0)
    assert len(out) == 1
    assert out[0].source_type == "metric_anomaly"
    assert out[0].content["z_score"] < -2


@pytest.mark.asyncio
async def test_collect_coo_action_failures(db_session, sample_company):
    db_session.add(
        CooAction(
            id=uuid.uuid4(),
            company_id=sample_company.id,
            action_type="employee_email",
            title="Email to ops manager",
            payload={"to_email": "x@y.z", "subject": "Hi", "body": "Hi"},
            status="failed",
            result={"error": "smtp blew up"},
        )
    )
    await db_session.flush()
    out = await collect_coo_action_failures(db_session)
    assert len(out) == 1


@pytest.mark.asyncio
async def test_run_all_collectors_summary(db_session, sample_company):
    counts = await run_all_collectors(db_session)
    for key in (
        "agent_task_failure",
        "approval_rejection_cluster",
        "metric_anomaly",
        "coo_action_failure",
    ):
        assert key in counts


@pytest.mark.asyncio
async def test_diagnose_without_llm_returns_stub(db_session, sample_company):
    obs = AgentObservation(
        id=uuid.uuid4(),
        company_id=sample_company.id,
        source_type="agent_task_failure",
        source_ref="x",
        title="A task failed",
        severity="medium",
        content={"task_type": "x", "error_message": "boom"},
        status="new",
    )
    db_session.add(obs)
    await db_session.flush()
    diag = await diagnose(db_session, obs.id)
    assert diag is not None
    assert diag.confidence == "low"
    assert diag.status == "proposed"
    # Observation flips to analyzed.
    refreshed = await db_session.get(AgentObservation, obs.id)
    assert refreshed.status == "analyzed"


@pytest.mark.asyncio
async def test_reviewer_without_llm_sets_concerns(db_session, sample_company):
    obs = AgentObservation(
        id=uuid.uuid4(),
        company_id=sample_company.id,
        source_type="agent_task_failure",
        source_ref="r",
        title="Failed",
        severity="medium",
        content={},
        status="new",
    )
    db_session.add(obs)
    await db_session.flush()
    diag = MonitorDiagnosis(
        id=uuid.uuid4(),
        observation_id=obs.id,
        root_cause_summary="?",
        proposed_fix="?",
        files_changed=[],
        confidence="medium",
        status="proposed",
    )
    db_session.add(diag)
    await db_session.flush()
    out = await review(db_session, diag.id)
    assert out is not None
    assert out.reviewer_agent_verdict["verdict"] == "concerns"


@pytest.mark.asyncio
async def test_github_render_pr_description():
    diag = MonitorDiagnosis(
        id=uuid.uuid4(),
        observation_id=uuid.uuid4(),
        root_cause_summary="Token expired.",
        proposed_fix="Refresh in the connector loop.",
        files_changed=[{"path": "x.py", "patch": "- old\n+ new"}],
        confidence="medium",
        status="proposed",
    )
    body = github.render_pr_description(diag)
    assert "Token expired" in body
    assert "x.py" in body


@pytest.mark.asyncio
async def test_github_open_draft_pr_skipped_without_config():
    diag = MonitorDiagnosis(
        id=uuid.uuid4(),
        observation_id=uuid.uuid4(),
        root_cause_summary="",
        confidence="low",
        status="proposed",
    )
    result = await github.open_draft_pr(diag)
    assert result["status"] == "skipped"
