from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class KnowledgeDocumentResponse(BaseModel):
    id: UUID
    company_id: UUID
    source_type: str
    source_ref: str | None
    title: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IngestResponse(BaseModel):
    document_id: UUID
    chunks: int
    changed: bool


class ReindexResponse(BaseModel):
    company_id: UUID
    started_at: str
    counts: dict[str, int]


class SearchResultChunk(BaseModel):
    chunk_id: str
    document_id: str
    company_id: str
    title: str
    source_type: str
    source_ref: str | None
    ordinal: int
    text: str
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultChunk]


class TranscriptUploadRequest(BaseModel):
    company_id: UUID
    title: str | None = None
    filename: str | None = None
    content: str


class DocumentUploadRequest(BaseModel):
    company_id: UUID
    source_type: str = "upload"
    source_ref: str | None = None
    title: str
    content: str
    meta: dict | None = None


class SynthesisRequest(BaseModel):
    company_id: UUID
    source_type: str = "meeting"
    lookback_days: int = 7
