"""
Diagnose a single AgentObservation — pull relevant context, ask Claude to
propose a fix, persist a MonitorDiagnosis.

The proposed fix is a unified-diff patch in ``proposed_fix`` plus a structured
``files_changed`` list of ``{"path", "patch"}``. No code is applied; the owner
approves each diagnosis and (if ``GITHUB_TOKEN`` is set) the router opens a
draft PR on their behalf when they approve.
"""
from __future__ import annotations

import json
import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.monitor import AgentObservation, MonitorDiagnosis
from app.services.ai import llm_client
from app.services.knowledge.retriever import format_chunks_for_prompt, retrieve

_DIAGNOSE_PROMPT = """You are an SRE-level engineer diagnosing failures in a
small business operations platform. You receive one observation describing
something that went wrong (a failed agent task, a recurring rejection, a
metric anomaly, or a failed action). You also have related context retrieved
from the company brain.

Produce a structured diagnosis. Return ONLY a JSON object matching this shape,
no prose around it:

{
  "root_cause_summary": "one or two sentences naming the most likely cause",
  "proposed_fix": "a concrete, minimal change — explain in prose what to alter",
  "files_changed": [
    {"path": "backend/path/to/file.py", "patch": "unified diff or pseudo-diff"}
  ],
  "confidence": "low" | "medium" | "high"
}

If you do not have enough context to propose a code change, set
``files_changed`` to an empty array and describe the diagnostic step the
owner should take next in ``proposed_fix``. Never invent files."""


async def diagnose(
    db: AsyncSession, observation_id: UUID
) -> MonitorDiagnosis | None:
    """Build a MonitorDiagnosis for one observation. Returns it, or None."""
    obs = (
        await db.execute(
            select(AgentObservation).where(AgentObservation.id == observation_id)
        )
    ).scalar_one_or_none()
    if obs is None:
        return None

    diagnosis = await _ask_llm_for_diagnosis(db, obs)

    record = MonitorDiagnosis(
        id=uuid.uuid4(),
        observation_id=obs.id,
        root_cause_summary=diagnosis.get("root_cause_summary"),
        proposed_fix=diagnosis.get("proposed_fix"),
        files_changed=diagnosis.get("files_changed") or [],
        confidence=diagnosis.get("confidence", "medium"),
        status="proposed",
    )
    db.add(record)
    obs.status = "analyzed"
    await db.flush()
    return record


async def _ask_llm_for_diagnosis(
    db: AsyncSession, obs: AgentObservation
) -> dict:
    """Run the diagnosis prompt with retrieved context. Falls back gracefully."""
    context_block = await _build_context_block(db, obs)
    user_payload = json.dumps(
        {
            "observation": {
                "source_type": obs.source_type,
                "source_ref": obs.source_ref,
                "title": obs.title,
                "severity": obs.severity,
                "content": obs.content,
            },
            "company_brain_context": context_block,
        },
        default=str,
    )

    if not llm_client.is_available():
        return {
            "root_cause_summary": (
                "LLM not configured; cannot auto-diagnose. Human review needed."
            ),
            "proposed_fix": (
                "Inspect this observation manually. "
                f"Severity: {obs.severity}. Details: {obs.content}"
            ),
            "files_changed": [],
            "confidence": "low",
        }

    try:
        result = await llm_client.complete(
            system=_DIAGNOSE_PROMPT,
            messages=[{"role": "user", "content": user_payload}],
            max_tokens=1200,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "root_cause_summary": f"LLM call failed: {exc}",
            "proposed_fix": "Retry the monitor or inspect logs.",
            "files_changed": [],
            "confidence": "low",
        }

    parsed = llm_client.extract_json(result["text"])
    if isinstance(parsed, dict):
        parsed.setdefault("root_cause_summary", "")
        parsed.setdefault("proposed_fix", "")
        parsed.setdefault("files_changed", [])
        parsed.setdefault("confidence", "medium")
        return parsed

    return {
        "root_cause_summary": "Model output could not be parsed.",
        "proposed_fix": result["text"][:1000] if result.get("text") else "",
        "files_changed": [],
        "confidence": "low",
    }


async def _build_context_block(
    db: AsyncSession, obs: AgentObservation, top_k: int = 6
) -> str:
    """Use the company brain to fetch relevant recent context, when possible."""
    if obs.company_id is None:
        return ""
    from app.models.core import Company

    company = (
        await db.execute(select(Company).where(Company.id == obs.company_id))
    ).scalar_one_or_none()
    if company is None:
        return ""
    query_parts = [obs.title]
    if isinstance(obs.content, dict):
        for key in ("task_type", "action_type", "error_message", "action_description"):
            v = obs.content.get(key)
            if v:
                query_parts.append(str(v))
    query = " ".join(query_parts)[:500]
    chunks = await retrieve(db, company.tenant_id, obs.company_id, query, top_k=top_k)
    return format_chunks_for_prompt(chunks, max_chars=2500)
