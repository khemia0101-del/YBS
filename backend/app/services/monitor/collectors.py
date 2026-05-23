"""
Collectors — scan the running system for things worth diagnosing.

Each collector reads recent activity and emits AgentObservation rows. Every
observation has a unique ``(source_type, source_ref)`` pair so re-running a
collector won't duplicate it.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from statistics import mean, pstdev
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentTask, ApprovalRequest
from app.models.business import MetricSnapshot
from app.models.coo import CooAction
from app.models.monitor import AgentObservation

_TERMINAL_FAILURE_STATUSES = ("terminal_failed", "failed", "error")


async def _create_observation(
    db: AsyncSession,
    *,
    source_type: str,
    source_ref: str,
    title: str,
    severity: str,
    content: dict,
    company_id: UUID | None = None,
) -> AgentObservation | None:
    """Insert an observation; silently skip if one already exists."""
    existing = await db.execute(
        select(AgentObservation).where(
            AgentObservation.source_type == source_type,
            AgentObservation.source_ref == source_ref,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return None
    obs = AgentObservation(
        id=uuid.uuid4(),
        company_id=company_id,
        source_type=source_type,
        source_ref=source_ref,
        title=title[:500],
        content=content,
        severity=severity,
        status="new",
    )
    db.add(obs)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return None
    return obs


async def collect_agent_task_failures(
    db: AsyncSession, since_hours: int = 48
) -> list[AgentObservation]:
    """Terminal/failed AgentTasks become observations."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    result = await db.execute(
        select(AgentTask).where(
            AgentTask.status.in_(_TERMINAL_FAILURE_STATUSES),
            AgentTask.updated_at >= cutoff,
        )
    )
    out: list[AgentObservation] = []
    for task in result.scalars().all():
        obs = await _create_observation(
            db,
            source_type="agent_task_failure",
            source_ref=str(task.id),
            title=f"Agent task failed: {task.task_type}",
            severity="medium",
            content={
                "task_type": task.task_type,
                "subject_type": task.subject_type,
                "subject_id": str(task.subject_id) if task.subject_id else None,
                "status": task.status,
                "retry_count": task.retry_count,
                "error_message": task.error_message,
                "input_params": task.input_params,
            },
            company_id=task.company_id,
        )
        if obs is not None:
            out.append(obs)
    return out


async def collect_approval_rejection_clusters(
    db: AsyncSession,
    *,
    threshold: int = 3,
    since_hours: int = 168,
) -> list[AgentObservation]:
    """A repeated pattern of approval rejections — a hint to revisit a rule."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    rows = (
        await db.execute(
            select(
                ApprovalRequest.company_id,
                ApprovalRequest.action_description,
                func.count(ApprovalRequest.id).label("n"),
            )
            .where(
                ApprovalRequest.status == "rejected",
                ApprovalRequest.created_at >= cutoff,
            )
            .group_by(ApprovalRequest.company_id, ApprovalRequest.action_description)
            .having(func.count(ApprovalRequest.id) >= threshold)
        )
    ).all()
    out: list[AgentObservation] = []
    for company_id, action_desc, count in rows:
        ref = f"{company_id}:{(action_desc or 'unknown')[:80]}"
        obs = await _create_observation(
            db,
            source_type="approval_rejection_cluster",
            source_ref=ref,
            title=f"Repeated rejections ({count}): {(action_desc or '?')[:60]}",
            severity="medium",
            content={
                "action_description": action_desc,
                "count": int(count),
                "since_hours": since_hours,
            },
            company_id=company_id,
        )
        if obs is not None:
            out.append(obs)
    return out


async def collect_metric_anomalies(
    db: AsyncSession, *, z_threshold: float = 2.0, min_history: int = 4
) -> list[AgentObservation]:
    """Latest metric snapshot more than ``z_threshold`` std-devs from history."""
    grouped: dict[UUID, list[MetricSnapshot]] = {}
    rows = (
        await db.execute(
            select(MetricSnapshot).order_by(
                MetricSnapshot.metric_definition_id,
                MetricSnapshot.period_date.desc(),
            )
        )
    ).scalars().all()
    for snap in rows:
        grouped.setdefault(snap.metric_definition_id, []).append(snap)

    out: list[AgentObservation] = []
    for metric_id, snaps in grouped.items():
        if len(snaps) < min_history + 1:
            continue
        snaps = sorted(snaps, key=lambda s: s.period_date)
        history = [float(s.value) for s in snaps[:-1]]
        latest = snaps[-1]
        if len(history) < min_history:
            continue
        avg = mean(history)
        sd = pstdev(history) or 0.0
        if sd == 0:
            continue
        z = (float(latest.value) - avg) / sd
        if abs(z) < z_threshold:
            continue
        obs = await _create_observation(
            db,
            source_type="metric_anomaly",
            source_ref=f"{metric_id}:{latest.period_date.isoformat()}",
            title=f"Metric anomaly on {latest.period_date}: z={z:.1f}",
            severity="high" if abs(z) >= 3 else "medium",
            content={
                "metric_definition_id": str(metric_id),
                "value": float(latest.value),
                "mean": round(avg, 4),
                "stdev": round(sd, 4),
                "z_score": round(z, 2),
                "period_date": latest.period_date.isoformat(),
            },
            company_id=latest.company_id,
        )
        if obs is not None:
            out.append(obs)
    return out


async def collect_coo_action_failures(
    db: AsyncSession, since_hours: int = 48
) -> list[AgentObservation]:
    """Failed COO actions — the propose/approve/execute chain broke at execute."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    result = await db.execute(
        select(CooAction).where(
            CooAction.status == "failed",
            CooAction.updated_at >= cutoff,
        )
    )
    out: list[AgentObservation] = []
    for action in result.scalars().all():
        obs = await _create_observation(
            db,
            source_type="coo_action_failure",
            source_ref=str(action.id),
            title=f"COO action failed: {action.action_type}",
            severity="medium",
            content={
                "action_type": action.action_type,
                "title": action.title,
                "payload": action.payload,
                "result": action.result,
            },
            company_id=action.company_id,
        )
        if obs is not None:
            out.append(obs)
    return out


async def run_all_collectors(db: AsyncSession) -> dict[str, int]:
    """Run every collector once. Returns counts per source_type."""
    counts = {
        "agent_task_failure": len(await collect_agent_task_failures(db)),
        "approval_rejection_cluster": len(
            await collect_approval_rejection_clusters(db)
        ),
        "metric_anomaly": len(await collect_metric_anomalies(db)),
        "coo_action_failure": len(await collect_coo_action_failures(db)),
    }
    return counts
