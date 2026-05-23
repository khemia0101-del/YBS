"""Company brain — upload, search, synthesize."""
from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import assert_company_in_tenant, get_tenant_id, require_analyst
from app.models.knowledge import KnowledgeDocument
from app.models.users import User
from app.schemas.knowledge import (
    DocumentUploadRequest,
    IngestResponse,
    KnowledgeDocumentResponse,
    ReindexResponse,
    SearchResponse,
    SearchResultChunk,
    SynthesisRequest,
    TranscriptUploadRequest,
)
from app.services.knowledge import recordings
from app.services.knowledge.ingest import ingest_document, reindex_company
from app.services.knowledge.retriever import retrieve
from app.services.knowledge.synthesizer import synthesize

router = APIRouter()


@router.post("/recordings/upload", response_model=IngestResponse)
async def upload_recording(
    body: TranscriptUploadRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user: User = Depends(require_analyst),
) -> IngestResponse:
    """Upload a meeting transcript (txt/vtt/srt/json) and index it."""
    await assert_company_in_tenant(db, body.company_id, tenant_id)
    parsed = recordings.parse_transcript(body.content, filename=body.filename)
    title = body.title or recordings.derive_title(parsed, fallback=body.filename)
    result = await ingest_document(
        db,
        company_id=body.company_id,
        source_type="meeting",
        source_ref=f"upload:{uuid.uuid4().hex[:12]}",
        title=title,
        content=parsed["content"],
        meta={
            "format": parsed["format"],
            "turns": len(parsed["turns"]),
            "started_at": parsed.get("started_at"),
        },
    )
    return IngestResponse(**result)


@router.post("/docs/upload", response_model=IngestResponse)
async def upload_document(
    body: DocumentUploadRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user: User = Depends(require_analyst),
) -> IngestResponse:
    """Upload an arbitrary text document into the company brain."""
    await assert_company_in_tenant(db, body.company_id, tenant_id)
    result = await ingest_document(
        db,
        company_id=body.company_id,
        source_type=body.source_type,
        source_ref=body.source_ref or f"upload:{uuid.uuid4().hex[:12]}",
        title=body.title,
        content=body.content,
        meta=body.meta,
    )
    return IngestResponse(**result)


@router.post("/reindex", response_model=ReindexResponse)
async def reindex(
    company_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user: User = Depends(require_analyst),
) -> ReindexResponse:
    """Re-run every already-connected adapter for one company."""
    await assert_company_in_tenant(db, company_id, tenant_id)
    result = await reindex_company(db, company_id)
    return ReindexResponse(company_id=UUID(result["company_id"]), **{
        k: result[k] for k in ("started_at", "counts")
    })


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1),
    company_id: UUID | None = Query(None),
    top_k: int = Query(8, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> SearchResponse:
    """Semantic (or keyword-fallback) search across the caller's tenant."""
    if company_id is not None:
        await assert_company_in_tenant(db, company_id, tenant_id)
    results = await retrieve(db, tenant_id, company_id, q, top_k=top_k)
    return SearchResponse(
        query=q,
        results=[SearchResultChunk(**r) for r in results],
    )


@router.get("/documents", response_model=list[KnowledgeDocumentResponse])
async def list_documents(
    company_id: UUID = Query(...),
    source_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> list[KnowledgeDocumentResponse]:
    await assert_company_in_tenant(db, company_id, tenant_id)
    stmt = (
        select(KnowledgeDocument)
        .where(KnowledgeDocument.company_id == company_id)
        .order_by(KnowledgeDocument.created_at.desc())
        .limit(limit)
    )
    if source_type:
        stmt = stmt.where(KnowledgeDocument.source_type == source_type)
    result = await db.execute(stmt)
    return [
        KnowledgeDocumentResponse.model_validate(d) for d in result.scalars().all()
    ]


@router.post("/synthesis", response_model=IngestResponse | None)
async def build_synthesis(
    body: SynthesisRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user: User = Depends(require_analyst),
) -> IngestResponse | None:
    """Produce a 'breadcrumbs' synthesis over a recent window of documents."""
    await assert_company_in_tenant(db, body.company_id, tenant_id)
    result = await synthesize(
        db,
        body.company_id,
        body.source_type,
        lookback_days=body.lookback_days,
    )
    return IngestResponse(**result) if result else None
