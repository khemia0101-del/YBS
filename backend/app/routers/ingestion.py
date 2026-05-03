from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_active_user, require_operator
from app.models.raw import RawRecord, StagedRecord
from app.models.sync import IntegrationCredential, SyncLog
from app.models.users import User
from app.schemas.raw import SyncStatusResponse, UploadResponse
from app.security.audit import write_audit_log

router = APIRouter()

ALLOWED_MIME_TYPES = {
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/pdf",
    "application/json",
    "text/plain",
}

SOURCE_SYSTEMS = ["quickbooks", "bank_csv", "payroll", "swept", "email", "manual"]


def _detect_source_system(filename: str, content_type: str) -> str:
    """Heuristic source system detection from filename and MIME type."""
    name = filename.lower()
    if "quickbooks" in name or "qbo" in name or "qb_" in name:
        return "quickbooks"
    if "payroll" in name or "paychex" in name or "adp" in name or "gusto" in name:
        return "payroll"
    if "bank" in name or "statement" in name or "checking" in name:
        return "bank_csv"
    if "swept" in name:
        return "swept"
    if content_type == "application/pdf":
        return "email"
    return "manual"


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    source_system: str | None = Query(None, description="Override auto-detected source system"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UploadResponse:
    """
    Accept a file upload, compute checksum for dedup, create a RawRecord,
    then enqueue async processing via Celery.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    checksum = hashlib.sha256(content).hexdigest()
    detected_system = source_system or _detect_source_system(
        file.filename or "", file.content_type or ""
    )

    # Duplicate detection by checksum
    existing = await db.execute(
        select(RawRecord).where(
            RawRecord.checksum == checksum, RawRecord.is_duplicate.is_(False)
        )
    )
    original = existing.scalar_one_or_none()

    if original is not None:
        return UploadResponse(
            raw_record_id=original.id,
            source_system=original.source_system,
            is_duplicate=True,
            duplicate_of=original.id,
            ingested_at=original.ingested_at,
        )

    raw = RawRecord(
        id=uuid.uuid4(),
        source_system=detected_system,
        source_ref=file.filename,
        raw_payload={"filename": file.filename, "content_type": file.content_type},
        checksum=checksum,
        ingested_by=current_user.id,
        is_duplicate=False,
    )
    db.add(raw)
    await db.flush()

    await write_audit_log(
        session=db,
        event_type="raw_record.uploaded",
        actor_id=current_user.id,
        actor_type="user",
        table_name="raw_records",
        record_id=raw.id,
        after_state={"source_system": detected_system, "filename": file.filename},
    )

    # Trigger async processing
    try:
        from app.workers.ingestion_tasks import process_uploaded_file

        process_uploaded_file.delay(str(raw.id))
    except Exception:
        pass  # Worker enqueue failure is non-fatal; record is still created

    return UploadResponse(
        raw_record_id=raw.id,
        source_system=detected_system,
        is_duplicate=False,
        duplicate_of=None,
        ingested_at=raw.ingested_at,
    )


@router.get("/status", response_model=list[SyncStatusResponse])
async def sync_status(db: AsyncSession = Depends(get_db)) -> list[SyncStatusResponse]:
    """Return last sync time and queue depth per source system."""
    results = []
    for system in SOURCE_SYSTEMS:
        # Latest completed sync log
        latest_result = await db.execute(
            select(SyncLog)
            .where(SyncLog.source_system == system, SyncLog.status == "completed")
            .order_by(SyncLog.started_at.desc())
            .limit(1)
        )
        latest = latest_result.scalar_one_or_none()

        # Queue depth = staged records pending for this source
        queue_q = await db.execute(
            select(func.count(StagedRecord.id))
            .join(RawRecord, StagedRecord.raw_record_id == RawRecord.id)
            .where(RawRecord.source_system == system, StagedRecord.status == "pending")
        )
        queue_depth = queue_q.scalar() or 0

        results.append(
            SyncStatusResponse(
                source_system=system,
                last_sync_at=latest.started_at if latest else None,
                last_sync_status=latest.status if latest else None,
                records_ingested_last_run=latest.records_ingested if latest else None,
                queue_depth=queue_depth,
            )
        )
    return results


@router.post("/quickbooks/sync")
async def trigger_qb_sync(
    realm_id: str = Query(..., description="QuickBooks realm/company ID"),
    since_iso: str | None = Query(None, description="ISO datetime to fetch changes since"),
    _user: User = Depends(require_operator),
) -> dict:
    """Enqueue a QuickBooks sync Celery task."""
    try:
        from app.workers.ingestion_tasks import sync_quickbooks

        task = sync_quickbooks.delay(realm_id, since_iso)
        return {"task_id": task.id, "status": "queued", "realm_id": realm_id}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not enqueue sync task: {exc}",
        )


@router.get("/quickbooks/auth-url")
async def qb_auth_url(_user: User = Depends(require_operator)) -> dict:
    """Return the QuickBooks OAuth2 authorization URL."""
    from urllib.parse import urlencode

    params = {
        "client_id": settings.QB_CLIENT_ID,
        "response_type": "code",
        "scope": "com.intuit.quickbooks.accounting",
        "redirect_uri": settings.QB_REDIRECT_URI,
        "state": uuid.uuid4().hex,
    }
    base = (
        "https://appcenter.intuit.com/connect/oauth2"
        if settings.QB_ENVIRONMENT == "production"
        else "https://appcenter.intuit.com/connect/oauth2"
    )
    return {"auth_url": f"{base}?{urlencode(params)}"}


@router.get("/quickbooks/callback")
async def qb_callback(
    code: str = Query(...),
    realm_id: str = Query(...),
    state: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """
    QuickBooks OAuth callback — exchange the auth code for tokens
    and persist them encrypted in integration_credentials.
    """
    import httpx

    token_url = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.QB_REDIRECT_URI,
            },
            auth=(settings.QB_CLIENT_ID, settings.QB_CLIENT_SECRET),
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"QB token exchange failed: {resp.text}",
        )

    tokens = resp.json()

    from app.security.encryption import vault

    # Store access_token
    from app.models.sync import IntegrationCredential

    cred = IntegrationCredential(
        id=uuid.uuid4(),
        company_id=current_user.id,  # Simplified — real impl maps realm_id to company
        source_system="quickbooks",
        credential_type="oauth_tokens",
        encrypted_value=vault.encrypt(str(tokens)),
        metadata_json={"realm_id": realm_id},
        expires_at=None,
        is_active=True,
    )
    db.add(cred)

    return {"status": "connected", "realm_id": realm_id}
