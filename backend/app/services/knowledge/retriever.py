"""
Retriever — top-k chunks for a query, scoped to one tenant/company.

Uses cosine similarity over stored embedding vectors when embeddings are
available. Falls back to a keyword-overlap score when the brain has no
embedding provider configured. Adequate for small-business scale; pgvector is
the natural upgrade path when chunk counts grow.
"""
from __future__ import annotations

import math
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.security.tenant import tenant_company_ids
from app.services.knowledge import embeddings


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


_TOKEN_RE = re.compile(r"[A-Za-z0-9']+")


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "") if len(t) > 2}


def _keyword_score(query_tokens: set[str], text: str) -> float:
    if not query_tokens:
        return 0.0
    chunk_tokens = _tokens(text)
    if not chunk_tokens:
        return 0.0
    overlap = query_tokens & chunk_tokens
    return len(overlap) / len(query_tokens)


async def retrieve(
    db: AsyncSession,
    tenant_id: UUID,
    company_id: UUID | None,
    query: str,
    top_k: int = 8,
    source_types: list[str] | None = None,
) -> list[dict]:
    """
    Return up to ``top_k`` matching chunks for ``query``, each as:

    ``{"chunk_id", "document_id", "company_id", "title", "source_type",
      "source_ref", "ordinal", "text", "score"}``

    Always scoped to the caller's tenant. If ``company_id`` is None the search
    spans every company in the tenant.
    """
    if not query or not query.strip():
        return []

    allowed_companies = (
        [company_id]
        if company_id is not None
        else await tenant_company_ids(db, tenant_id)
    )
    if not allowed_companies:
        return []

    stmt = (
        select(KnowledgeChunk, KnowledgeDocument)
        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .where(
            KnowledgeChunk.company_id.in_(allowed_companies),
            KnowledgeDocument.status == "active",
        )
    )
    if source_types:
        stmt = stmt.where(KnowledgeDocument.source_type.in_(source_types))

    rows = (await db.execute(stmt)).all()
    if not rows:
        return []

    query_vector: list[float] = []
    if embeddings.is_available():
        try:
            query_vector = await embeddings.embed_one(query, input_type="query")
        except Exception:
            query_vector = []

    qt = _tokens(query)
    scored: list[tuple[float, KnowledgeChunk, KnowledgeDocument]] = []
    for chunk, doc in rows:
        if query_vector and chunk.embedding:
            score = _cosine(query_vector, chunk.embedding)
        else:
            score = _keyword_score(qt, chunk.text)
        if score > 0:
            scored.append((score, chunk, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    out: list[dict] = []
    for score, chunk, doc in scored[:top_k]:
        out.append(
            {
                "chunk_id": str(chunk.id),
                "document_id": str(doc.id),
                "company_id": str(doc.company_id),
                "title": doc.title,
                "source_type": doc.source_type,
                "source_ref": doc.source_ref,
                "ordinal": chunk.ordinal,
                "text": chunk.text,
                "score": round(score, 4),
            }
        )
    return out


def format_chunks_for_prompt(chunks: list[dict], max_chars: int = 4000) -> str:
    """Render retrieved chunks as a compact context block for an LLM prompt."""
    if not chunks:
        return ""
    lines: list[str] = []
    total = 0
    for i, c in enumerate(chunks, start=1):
        header = f"[{i}] ({c['source_type']}) {c['title']}"
        body = c["text"].strip()
        block = f"{header}\n{body}"
        if total + len(block) > max_chars and lines:
            break
        lines.append(block)
        total += len(block)
    return "\n\n".join(lines)
