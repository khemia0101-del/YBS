"""
Reviewer — second LLM pass that critiques a MonitorDiagnosis before a human
sees it. Adds a ``reviewer_agent_verdict`` to the diagnosis so the human can
decide based on two opinions.
"""
from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.monitor import AgentObservation, MonitorDiagnosis
from app.services.ai import llm_client

_REVIEW_PROMPT = """You are a careful senior engineer reviewing another
agent's proposed fix for a production failure. Decide whether the fix
addresses the root cause without introducing obvious new risk.

Return ONLY a JSON object:

{
  "verdict": "approve" | "concerns" | "reject",
  "notes": "1-3 sentences explaining the verdict"
}

Bias toward "concerns" if the diagnosis is vague or the patch is empty.
Reject only when the fix would clearly make things worse."""


async def review(db: AsyncSession, diagnosis_id: UUID) -> MonitorDiagnosis | None:
    diag = (
        await db.execute(
            select(MonitorDiagnosis).where(MonitorDiagnosis.id == diagnosis_id)
        )
    ).scalar_one_or_none()
    if diag is None:
        return None
    obs = (
        await db.execute(
            select(AgentObservation).where(
                AgentObservation.id == diag.observation_id
            )
        )
    ).scalar_one_or_none()
    if obs is None:
        return diag

    payload = json.dumps(
        {
            "observation": {
                "title": obs.title,
                "source_type": obs.source_type,
                "content": obs.content,
            },
            "diagnosis": {
                "root_cause_summary": diag.root_cause_summary,
                "proposed_fix": diag.proposed_fix,
                "files_changed": diag.files_changed,
                "confidence": diag.confidence,
            },
        },
        default=str,
    )

    if not llm_client.is_available():
        diag.reviewer_agent_verdict = {
            "verdict": "concerns",
            "notes": "LLM not configured; no automated review performed.",
        }
        await db.flush()
        return diag

    try:
        result = await llm_client.complete(
            system=_REVIEW_PROMPT,
            messages=[{"role": "user", "content": payload}],
            max_tokens=400,
        )
        parsed = llm_client.extract_json(result["text"])
    except Exception as exc:  # noqa: BLE001
        parsed = {"verdict": "concerns", "notes": f"Review failed: {exc}"}

    if not isinstance(parsed, dict) or "verdict" not in parsed:
        parsed = {"verdict": "concerns", "notes": "Review output not parseable."}

    diag.reviewer_agent_verdict = parsed
    await db.flush()
    return diag
