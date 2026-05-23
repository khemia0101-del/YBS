"""
Synthesizer — periodic "breadcrumbs" rollups.

Given a set of recent KnowledgeDocuments of a single source type, ask Claude
to produce a short 1-page synthesis and store it as its own KnowledgeDocument
(``source_type="synthesis"``) so it shows up in retrieval like anything else.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeDocument
from app.services.ai import llm_client
from app.services.knowledge.ingest import ingest_document

_SYNTH_PROMPT = """You synthesize a small business's recent {kind} into a
one-page briefing for the owner. Lead with the three to five most important
points. Each point should be a complete sentence with the specific names,
numbers, or commitments mentioned. Skip pleasantries. If there's a clear
next action, name it last. Keep it under 250 words."""


async def synthesize(
    db: AsyncSession,
    company_id: UUID,
    source_type: str,
    *,
    lookback_days: int = 7,
    max_docs: int = 20,
) -> dict | None:
    """
    Build a synthesis document from the most recent ``source_type`` docs for
    this company. Returns the ingest result or ``None`` when nothing to do.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    result = await db.execute(
        select(KnowledgeDocument)
        .where(
            KnowledgeDocument.company_id == company_id,
            KnowledgeDocument.source_type == source_type,
            KnowledgeDocument.status == "active",
            KnowledgeDocument.created_at >= cutoff,
        )
        .order_by(KnowledgeDocument.created_at.desc())
        .limit(max_docs)
    )
    docs = result.scalars().all()
    if not docs:
        return None

    bundle = "\n\n---\n\n".join(
        f"# {d.title} ({d.created_at:%Y-%m-%d})\n{d.content[:2000]}" for d in docs
    )

    if llm_client.is_available():
        kind = {
            "meeting": "meetings",
            "email": "emails",
            "interview": "interviews",
            "profit_recommendation": "profit recommendations",
            "agent_action": "agent actions",
        }.get(source_type, source_type)
        try:
            result = await llm_client.complete(
                system=_SYNTH_PROMPT.format(kind=kind),
                messages=[{"role": "user", "content": bundle}],
                max_tokens=600,
            )
            synthesis = result["text"].strip()
        except Exception as exc:  # noqa: BLE001
            synthesis = f"(synthesis failed: {exc})\n\n{_fallback_summary(docs)}"
    else:
        synthesis = _fallback_summary(docs)

    ref = f"{source_type}:{datetime.utcnow().date().isoformat()}"
    title = f"Synthesis — {source_type} (last {lookback_days}d)"
    return await ingest_document(
        db,
        company_id=company_id,
        source_type="synthesis",
        source_ref=ref,
        title=title,
        content=synthesis,
        meta={"of_source_type": source_type, "doc_count": len(docs)},
    )


def _fallback_summary(docs) -> str:
    """No-LLM fallback: just stitch document titles + first lines."""
    lines = [f"Recent items ({len(docs)}):"]
    for d in docs:
        first_line = (d.content or "").splitlines()[0] if d.content else ""
        lines.append(f"- {d.title}: {first_line[:120]}")
    return "\n".join(lines)
