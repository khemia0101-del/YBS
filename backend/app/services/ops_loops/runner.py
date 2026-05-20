"""
OpsLoop runner — execute one loop iteration.

Builds context (live business briefing + retrieved company-brain chunks),
asks Claude with the COO action tools to propose 0-N CooActions, persists
each as ``status="pending"`` for owner approval. Records an OpsLoopRun.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coo import CooAction
from app.models.core import Company
from app.models.monitor import AgentObservation
from app.models.ops_loop import OpsLoop, OpsLoopRun
from app.services.ai import llm_client
from app.services.coo.assistant import (
    ACTION_TOOLS,
    _TOOL_TO_ACTION,
    build_context,
)


_LOOP_SYSTEM = """You are a continuously-running operations agent for a small
business. The owner relies on you to keep an eye on a single focus area
({focus}) without prompting. On each cycle you read the live business
briefing below and produce two things:

1. A short ``findings`` summary (2-5 bullets) describing what changed since
   the last cycle and what matters now.
2. Zero or more proposed actions via your tools. Propose ONLY when there is
   a concrete, useful step. Quality over quantity. Every tool call becomes a
   pending action the owner must approve with one tap — nothing executes
   automatically.

Be concrete and reference the real numbers from the briefing."""


async def run_loop(db: AsyncSession, loop_id: UUID) -> OpsLoopRun:
    """Execute one iteration of an OpsLoop. Persists and returns the OpsLoopRun."""
    loop = (
        await db.execute(select(OpsLoop).where(OpsLoop.id == loop_id))
    ).scalar_one_or_none()
    if loop is None:
        raise ValueError(f"OpsLoop {loop_id} not found")

    run = OpsLoopRun(
        id=uuid.uuid4(),
        loop_id=loop.id,
        started_at=datetime.now(timezone.utc),
        status="running",
        proposed_actions_count=0,
    )
    db.add(run)
    await db.flush()

    try:
        context_text = await build_context(db, loop.company_id, query=loop.prompt)
        recent_observations = await _recent_observations(db, loop.company_id)
        if recent_observations:
            context_text += "\n\nRecent monitor observations:\n" + recent_observations

        findings_text, actions = await _ask_llm(loop, context_text)

        for action_type, title, payload in actions:
            db.add(
                CooAction(
                    id=uuid.uuid4(),
                    company_id=loop.company_id,
                    action_type=action_type,
                    title=title,
                    payload=payload,
                    status="pending",
                )
            )
        run.proposed_actions_count = len(actions)
        run.findings_summary = findings_text or "No findings."
        run.status = "succeeded"
        loop.last_run_at = datetime.now(timezone.utc)
    except Exception as exc:  # noqa: BLE001 — surface runner-level failures
        run.status = "failed"
        run.error = str(exc)[:1000]
    finally:
        run.ended_at = datetime.now(timezone.utc)
        await db.flush()
    return run


async def _recent_observations(
    db: AsyncSession, company_id: UUID, limit: int = 5
) -> str:
    rows = (
        await db.execute(
            select(AgentObservation)
            .where(AgentObservation.company_id == company_id)
            .order_by(AgentObservation.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    if not rows:
        return ""
    return "\n".join(f"- [{o.severity}] {o.title}" for o in rows)


async def _ask_llm(
    loop: OpsLoop, context_text: str
) -> tuple[str, list[tuple[str, str, dict]]]:
    """Drive the LLM. Returns (findings_text, [(action_type, title, payload)])."""
    if not llm_client.is_available():
        return (
            "AI not configured (no ANTHROPIC_API_KEY). Briefing only:\n"
            + context_text[:1500],
            [],
        )

    system = _LOOP_SYSTEM.format(focus=loop.focus)
    user = (
        f"Loop name: {loop.name}\n"
        f"Focus: {loop.focus}\n"
        f"Loop directive: {loop.prompt}\n\n"
        f"# Live briefing\n{context_text}"
    )
    result = await llm_client.complete(
        system=system,
        messages=[{"role": "user", "content": user}],
        max_tokens=1400,
        tools=ACTION_TOOLS,
    )

    actions: list[tuple[str, str, dict]] = []
    for tu in result["tool_use"]:
        action_type = _TOOL_TO_ACTION.get(tu["name"])
        if action_type is None:
            continue
        payload = tu["input"]
        if action_type == "employee_email":
            title = f"Email: {payload.get('subject', '(no subject)')}"
        elif action_type == "employee_task":
            title = f"Task: {payload.get('title', '(untitled)')}"
        else:
            title = payload.get("title", "Proposed change")
        actions.append((action_type, title, payload))

    return result["text"].strip(), actions
