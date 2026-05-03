from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RawRecordResponse(BaseModel):
    id: UUID
    source_system: str
    source_ref: str | None
    file_s3_key: str | None
    checksum: str | None
    ingested_at: datetime
    is_duplicate: bool
    duplicate_of: UUID | None

    model_config = ConfigDict(from_attributes=True)


class UploadResponse(BaseModel):
    raw_record_id: UUID
    source_system: str
    is_duplicate: bool
    duplicate_of: UUID | None
    ingested_at: datetime
    staged_record_id: UUID | None = None
    confidence_score: float | None = None


class SyncStatusResponse(BaseModel):
    source_system: str
    last_sync_at: datetime | None
    last_sync_status: str | None
    records_ingested_last_run: int | None
    queue_depth: int
