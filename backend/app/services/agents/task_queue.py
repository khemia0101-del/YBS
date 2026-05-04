from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentActionLog, AgentTask
from app.security.rbac import AGENT_WRITE_PROHIBITED, AgentGuardrailViolation, validate_agent_writes


async def enqueue_task(
    session: AsyncSession,
    task_type: str,
    company_id: UUID,
    input_params: dict,
    priority: int = 5,
    agent_id: str = "hermes",
    parent_task_id: UUID | None = None,
    scheduled_at: datetime | None = None,
    subject_type: str | None = None,
    subject_id: UUID | None = None,
) -> UUID:
    """
    Create a new AgentTask in 'queued' status and return its id.
    Does NOT commit — caller is responsible.
    """
    task = AgentTask(
        id=uuid.uuid4(),
        task_type=task_type,
        company_id=company_id,
        input_params=input_params,
        priority=priority,
        agent_id=agent_id,
        parent_task_id=parent_task_id,
        scheduled_at=scheduled_at,
        subject_type=subject_type,
        subject_id=subject_id,
        status="queued",
    )
    session.add(task)
    await session.flush()
    return task.id


async def claim_next_task(
    session: AsyncSession,
    agent_id: str,
    task_types: list[str] | None = None,
) -> AgentTask | None:
    """
    Atomically claim the next queued task for this agent using
    SELECT FOR UPDATE SKIP LOCKED to prevent double-claiming.
    """
    now = datetime.now(timezone.utc)
    q = (
        select(AgentTask)
        .where(
            AgentTask.agent_id == agent_id,
            AgentTask.status == "queued",
            (AgentTask.scheduled_at.is_(None)) | (AgentTask.scheduled_at <= now),
        )
        .order_by(AgentTask.priority.asc(), AgentTask.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if task_types:
        q = q.where(AgentTask.task_type.in_(task_types))

    result = await session.execute(q)
    task = result.scalar_one_or_none()
    if task is None:
        return None

    task.status = "running"
    task.started_at = now
    await session.flush()
    return task


async def complete_task(
    session: AsyncSession,
    task_id: UUID,
    output_data: dict,
    tables_written: list[str],
    actor_type: str = "agent",
    action_type: str = "task_completion",
    description: str | None = None,
    tables_read: list[str] | None = None,
) -> None:
    """
    Mark a task as completed. Enforces agent write guardrails
    and writes an immutable AgentActionLog entry.
    """
    # Guardrail: reject prohibited writes
    validate_agent_writes(actor_type, tables_written)

    result = await session.execute(select(AgentTask).where(AgentTask.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise ValueError(f"Task {task_id} not found")

    now = datetime.now(timezone.utc)
    task.status = "completed"
    task.completed_at = now
    task.output_data = output_data

    log = AgentActionLog(
        id=uuid.uuid4(),
        task_id=task_id,
        agent_id=task.agent_id,
        action_type=action_type,
        description=description or f"Task {task.task_type} completed",
        output_snapshot=output_data,
        tables_read=tables_read or [],
        tables_written=tables_written,
        was_approved=None,
    )
    session.add(log)
    await session.flush()


async def fail_task(
    session: AsyncSession,
    task_id: UUID,
    error_message: str,
) -> None:
    """
    Increment retry_count. If below max_retries, requeue with exponential backoff.
    Otherwise, set to terminal_failed and (optionally) notify operator.
    """
    result = await session.execute(select(AgentTask).where(AgentTask.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise ValueError(f"Task {task_id} not found")

    task.retry_count += 1
    task.error_message = error_message

    if task.retry_count < task.max_retries:
        # Exponential backoff: 2^retry_count minutes
        delay_minutes = 2 ** task.retry_count
        task.scheduled_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
        task.status = "queued"
        task.started_at = None
    else:
        task.status = "terminal_failed"
        task.completed_at = datetime.now(timezone.utc)
        # Attempt to notify operator via Telegram
        await _notify_terminal_failure(task, error_message)

    await session.flush()


async def request_approval(
    session: AsyncSession,
    task_id: UUID,
    company_id: UUID,
    subject_description: str,
    action_description: str,
    risk_level: str = "medium",
    required_role: str = "analyst",
    expires_hours: int = 24,
) -> UUID:
    """
    Transition a task to awaiting_approval and create an ApprovalRequest.
    Returns the ApprovalRequest.id.
    """
    from app.models.agent import ApprovalRequest

    result = await session.execute(select(AgentTask).where(AgentTask.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise ValueError(f"Task {task_id} not found")

    task.status = "awaiting_approval"

    req = ApprovalRequest(
        id=uuid.uuid4(),
        company_id=company_id,
        task_id=task_id,
        requested_by=task.agent_id,
        subject_description=subject_description,
        action_description=action_description,
        risk_level=risk_level,
        required_role=required_role,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_hours),
    )
    session.add(req)
    await session.flush()
    return req.id


async def _notify_terminal_failure(task: AgentTask, error: str) -> None:
    """Send a Telegram notification for terminal failures. Fire-and-forget."""
    from app.config import settings

    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_OPERATOR_CHAT_ID:
        return

    try:
        import httpx

        msg = (
            f"🚨 AGENT TASK TERMINAL FAILURE\n"
            f"Task ID: {task.id}\n"
            f"Type: {task.task_type}\n"
            f"Agent: {task.agent_id}\n"
            f"Error: {error[:500]}\n"
            f"Retries: {task.retry_count}/{task.max_retries}"
        )
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(url, json={"chat_id": settings.TELEGRAM_OPERATOR_CHAT_ID, "text": msg})
    except Exception:
        pass  # Notification failure must not crash the task management flow
