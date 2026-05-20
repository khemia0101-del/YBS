"""
Ingest adapters — pull from already-connected sources into KnowledgeDocuments.

Each adapter is idempotent: it looks up existing KnowledgeDocuments by
``(company_id, source_type, source_ref)`` and updates them if the underlying
artifact has changed. After writing a document we (re)build its chunks and,
when an embeddings provider is configured, populate embedding vectors.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentActionLog
from app.models.business import MetricDefinition, MetricSnapshot
from app.models.esop import QoERun
from app.models.interview import InterviewMessage, InterviewSession
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.models.profit import ProfitRecommendation
from app.models.raw import RawRecord
from app.services.knowledge import embeddings
from app.services.knowledge.chunker import chunk_text, estimate_tokens


def _checksum(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


async def _upsert_document(
    db: AsyncSession,
    *,
    company_id: UUID,
    source_type: str,
    source_ref: str,
    title: str,
    content: str,
    meta: dict | None = None,
) -> tuple[KnowledgeDocument, bool]:
    """Upsert a document. Returns (doc, content_changed)."""
    result = await db.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.company_id == company_id,
            KnowledgeDocument.source_type == source_type,
            KnowledgeDocument.source_ref == source_ref,
        )
    )
    doc = result.scalar_one_or_none()
    new_checksum = _checksum(content)
    if doc is None:
        doc = KnowledgeDocument(
            id=uuid.uuid4(),
            company_id=company_id,
            source_type=source_type,
            source_ref=source_ref,
            title=title[:500],
            content=content,
            meta={**(meta or {}), "checksum": new_checksum},
            status="active",
        )
        db.add(doc)
        await db.flush()
        return doc, True

    prior = (doc.meta or {}).get("checksum")
    if prior == new_checksum:
        return doc, False
    doc.title = title[:500]
    doc.content = content
    doc.meta = {**(doc.meta or {}), "checksum": new_checksum, **(meta or {})}
    doc.status = "active"
    await db.flush()
    return doc, True


async def _rebuild_chunks(db: AsyncSession, doc: KnowledgeDocument) -> int:
    """Re-chunk a document and (when configured) re-embed its chunks."""
    await db.execute(
        delete(KnowledgeChunk).where(KnowledgeChunk.document_id == doc.id)
    )
    pieces = chunk_text(doc.content)
    if not pieces:
        return 0

    vectors: list[list[float]] = []
    if embeddings.is_available():
        try:
            vectors = await embeddings.embed(pieces, input_type="document")
        except Exception:
            vectors = []

    for i, piece in enumerate(pieces):
        chunk = KnowledgeChunk(
            id=uuid.uuid4(),
            document_id=doc.id,
            company_id=doc.company_id,
            ordinal=i,
            text=piece,
            embedding=vectors[i] if i < len(vectors) else None,
            token_count=estimate_tokens(piece),
        )
        db.add(chunk)
    await db.flush()
    return len(pieces)


async def ingest_document(
    db: AsyncSession,
    *,
    company_id: UUID,
    source_type: str,
    source_ref: str,
    title: str,
    content: str,
    meta: dict | None = None,
) -> dict:
    """Generic upsert + chunk path used by every adapter and by the upload routes."""
    doc, changed = await _upsert_document(
        db,
        company_id=company_id,
        source_type=source_type,
        source_ref=source_ref,
        title=title,
        content=content,
        meta=meta,
    )
    if changed:
        chunk_count = await _rebuild_chunks(db, doc)
    else:
        result = await db.execute(
            select(KnowledgeChunk.id).where(KnowledgeChunk.document_id == doc.id)
        )
        chunk_count = len(result.all())
    return {
        "document_id": str(doc.id),
        "chunks": chunk_count,
        "changed": changed,
    }


# ---------------------------------------------------------------------------
# Source-specific adapters
# ---------------------------------------------------------------------------


async def ingest_gmail_messages(
    db: AsyncSession, company_id: UUID, limit: int = 200
) -> int:
    """Index Gmail message bodies stored as RawRecords."""
    result = await db.execute(
        select(RawRecord)
        .where(
            RawRecord.company_id == company_id,
            RawRecord.source_system == "gmail",
        )
        .order_by(RawRecord.ingested_at.desc())
        .limit(limit)
    )
    count = 0
    for record in result.scalars().all():
        payload = record.raw_payload or {}
        body = (
            payload.get("body_text")
            or payload.get("snippet")
            or payload.get("body")
            or ""
        )
        subject = payload.get("subject") or "(no subject)"
        sender = payload.get("from") or payload.get("sender") or ""
        if not body.strip():
            continue
        content = f"From: {sender}\nSubject: {subject}\n\n{body}".strip()
        await ingest_document(
            db,
            company_id=company_id,
            source_type="email",
            source_ref=str(record.id),
            title=f"Email: {subject}",
            content=content,
            meta={"sender": sender},
        )
        count += 1
    return count


async def ingest_interview_session(
    db: AsyncSession, session_id: UUID
) -> dict | None:
    """Index one interview session as a single threaded document."""
    session = (
        await db.execute(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
    ).scalar_one_or_none()
    if session is None:
        return None
    msgs = (
        await db.execute(
            select(InterviewMessage)
            .where(InterviewMessage.session_id == session_id)
            .order_by(InterviewMessage.seq)
        )
    ).scalars().all()
    if not msgs:
        return None
    body = "\n".join(f"{m.sender}: {m.content}" for m in msgs)
    title = (
        f"Interview ({session.purpose}) — {session.interviewee_name or session.role}"
    )
    return await ingest_document(
        db,
        company_id=session.company_id,
        source_type="interview",
        source_ref=str(session.id),
        title=title,
        content=body,
        meta={"role": session.role, "purpose": session.purpose},
    )


async def ingest_qoe_run(db: AsyncSession, run_id: UUID) -> dict | None:
    run = (
        await db.execute(select(QoERun).where(QoERun.id == run_id))
    ).scalar_one_or_none()
    if run is None:
        return None
    summary_lines = [
        f"QoE run {run.run_date}",
        f"Reported EBITDA: {run.reported_ebitda}",
        f"Adjusted EBITDA: {run.adjusted_ebitda}",
        f"SDE: {run.normalized_ebitda}",
    ]
    evidence = run.evidence_bundle or {}
    if isinstance(evidence, dict):
        qoe = evidence.get("qoe") or {}
        for period in qoe.get("periods", []) or []:
            summary_lines.append(
                f"- {period.get('label')}: revenue={period.get('revenue')}, "
                f"op_income={period.get('operating_income')}"
            )
    return await ingest_document(
        db,
        company_id=run.company_id,
        source_type="qoe",
        source_ref=str(run.id),
        title=f"QoE — {run.run_date}",
        content="\n".join(summary_lines),
        meta={"status": run.status},
    )


async def ingest_profit_recommendations(
    db: AsyncSession, company_id: UUID
) -> int:
    """Index each profit recommendation as a document."""
    result = await db.execute(
        select(ProfitRecommendation).where(
            ProfitRecommendation.company_id == company_id
        )
    )
    count = 0
    for rec in result.scalars().all():
        rationale = rec.rationale or ""
        impact = (
            f"${rec.estimated_annual_impact:,.0f}/yr"
            if rec.estimated_annual_impact is not None
            else "impact TBD"
        )
        content = (
            f"Title: {rec.title}\nImpact: {impact}\nCategory: {rec.category}\n\n"
            f"{rationale}"
        )
        await ingest_document(
            db,
            company_id=company_id,
            source_type="profit_recommendation",
            source_ref=str(rec.id),
            title=rec.title,
            content=content,
            meta={"category": rec.category},
        )
        count += 1
    return count


async def ingest_metric_trends(db: AsyncSession, company_id: UUID) -> int:
    """Index one document per metric definition summarizing its recent trend."""
    defs = (
        await db.execute(
            select(MetricDefinition).where(MetricDefinition.company_id == company_id)
        )
    ).scalars().all()
    count = 0
    for d in defs:
        snaps = (
            await db.execute(
                select(MetricSnapshot)
                .where(MetricSnapshot.metric_definition_id == d.id)
                .order_by(MetricSnapshot.period_date.desc())
                .limit(12)
            )
        ).scalars().all()
        if not snaps:
            continue
        lines = [f"Metric: {d.name} ({d.unit})", f"Target: {d.target_value}"]
        for s in reversed(snaps):
            lines.append(f"- {s.period_date}: {s.value}")
        await ingest_document(
            db,
            company_id=company_id,
            source_type="metric_trend",
            source_ref=str(d.id),
            title=f"Metric trend: {d.name}",
            content="\n".join(lines),
            meta={"category": d.category, "is_north_star": d.is_north_star},
        )
        count += 1
    return count


async def ingest_agent_actions(
    db: AsyncSession, company_id: UUID, limit: int = 200
) -> int:
    """Index recent AgentActionLog descriptions for the company."""
    result = await db.execute(
        select(AgentActionLog)
        .order_by(AgentActionLog.created_at.desc())
        .limit(limit)
    )
    count = 0
    for log in result.scalars().all():
        if not log.description:
            continue
        await ingest_document(
            db,
            company_id=company_id,
            source_type="agent_action",
            source_ref=str(log.id),
            title=f"Agent action: {log.action_type}",
            content=log.description,
            meta={"agent_id": log.agent_id, "action_type": log.action_type},
        )
        count += 1
    return count


async def reindex_company(db: AsyncSession, company_id: UUID) -> dict:
    """Run every already-connected adapter for one company."""
    started = datetime.utcnow()
    counts = {
        "email": await ingest_gmail_messages(db, company_id),
        "profit_recommendation": await ingest_profit_recommendations(db, company_id),
        "metric_trend": await ingest_metric_trends(db, company_id),
        "agent_action": await ingest_agent_actions(db, company_id),
    }
    sessions = (
        await db.execute(
            select(InterviewSession.id).where(
                InterviewSession.company_id == company_id
            )
        )
    ).all()
    interview_count = 0
    for row in sessions:
        if await ingest_interview_session(db, row[0]) is not None:
            interview_count += 1
    counts["interview"] = interview_count

    qoe_runs = (
        await db.execute(
            select(QoERun.id).where(QoERun.company_id == company_id)
        )
    ).all()
    qoe_count = 0
    for row in qoe_runs:
        if await ingest_qoe_run(db, row[0]) is not None:
            qoe_count += 1
    counts["qoe"] = qoe_count

    return {
        "company_id": str(company_id),
        "started_at": started.isoformat(),
        "counts": counts,
    }
