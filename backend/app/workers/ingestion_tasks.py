from __future__ import annotations

import asyncio
import hashlib
import uuid
from datetime import datetime, timezone

from app.workers.celery_app import app as celery_app


def _run_async(coro):
    """Run a coroutine in a new event loop (safe for Celery workers)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=2,
    name="app.workers.ingestion_tasks.sync_quickbooks",
)
def sync_quickbooks(self, realm_id: str, since_iso: str | None = None) -> dict:
    """
    Pull transactions from QuickBooks API for the given realm.
    Returns summary dict with fetched/new/duplicates/failed counts.
    """
    try:
        return _run_async(_sync_quickbooks_async(realm_id, since_iso))
    except Exception as exc:
        raise self.retry(exc=exc)


async def _sync_quickbooks_async(realm_id: str, since_iso: str | None) -> dict:
    from app.config import settings
    from app.database import AsyncSessionLocal
    from app.models.raw import RawRecord
    from app.models.sync import SyncLog
    from sqlalchemy import select
    import httpx

    async with AsyncSessionLocal() as session:
        log = SyncLog(
            id=uuid.uuid4(),
            source_system="quickbooks",
            realm_id=realm_id,
            status="running",
        )
        session.add(log)
        await session.commit()

        fetched = 0
        new_count = 0
        duplicates = 0
        failed = 0
        errors = []

        try:
            # Retrieve stored tokens for this realm
            from app.models.sync import IntegrationCredential
            from app.security.encryption import vault

            cred_result = await session.execute(
                select(IntegrationCredential).where(
                    IntegrationCredential.source_system == "quickbooks",
                    IntegrationCredential.is_active.is_(True),
                    IntegrationCredential.metadata_json.op("->>")(
                        "realm_id"
                    ) == realm_id,
                )
            )
            cred = cred_result.scalar_one_or_none()
            if cred is None:
                raise ValueError(f"No active QB credentials for realm {realm_id}")

            import ast
            tokens = ast.literal_eval(vault.decrypt(cred.encrypted_value))
            access_token = tokens.get("access_token", "")

            # Fetch invoices from QB API
            base_url = (
                "https://quickbooks.api.intuit.com"
                if settings.QB_ENVIRONMENT == "production"
                else "https://sandbox-quickbooks.api.intuit.com"
            )
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }
            query = "SELECT * FROM Invoice MAXRESULTS 1000"
            if since_iso:
                query = f"SELECT * FROM Invoice WHERE MetaData.LastUpdatedTime >= '{since_iso}' MAXRESULTS 1000"

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{base_url}/v3/company/{realm_id}/query",
                    params={"query": query, "minorversion": "65"},
                    headers=headers,
                )

            if resp.status_code != 200:
                raise ValueError(f"QB API error {resp.status_code}: {resp.text[:500]}")

            data = resp.json()
            invoices = data.get("QueryResponse", {}).get("Invoice", [])
            fetched = len(invoices)

            for inv in invoices:
                checksum = hashlib.sha256(str(inv).encode()).hexdigest()
                existing = await session.execute(
                    select(RawRecord).where(
                        RawRecord.checksum == checksum, RawRecord.is_duplicate.is_(False)
                    )
                )
                if existing.scalar_one_or_none():
                    duplicates += 1
                    continue

                raw = RawRecord(
                    id=uuid.uuid4(),
                    source_system="quickbooks",
                    source_ref=inv.get("Id"),
                    raw_payload=inv,
                    checksum=checksum,
                    is_duplicate=False,
                )
                session.add(raw)
                new_count += 1

            await session.flush()

            # Update sync log
            log.status = "completed"
            log.ended_at = datetime.now(timezone.utc)
            log.records_ingested = new_count
            await session.commit()

        except Exception as exc:
            failed += 1
            errors.append(str(exc))
            log.status = "failed"
            log.ended_at = datetime.now(timezone.utc)
            log.errors_json = errors
            await session.commit()
            raise

        return {
            "realm_id": realm_id,
            "fetched": fetched,
            "new": new_count,
            "duplicates": duplicates,
            "failed": failed,
        }


@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.workers.ingestion_tasks.process_uploaded_file",
)
def process_uploaded_file(self, raw_record_id: str) -> dict:
    """
    Post-upload processing pipeline:
    1. Classify file type
    2. Extract structured data
    3. Run fuzzy matching for entity resolution
    4. Score confidence
    5. Auto-approve if above threshold, else mark needs_review
    """
    try:
        return _run_async(_process_file_async(raw_record_id))
    except Exception as exc:
        raise self.retry(exc=exc)


async def _process_file_async(raw_record_id: str) -> dict:
    from app.config import settings
    from app.database import AsyncSessionLocal
    from app.models.raw import RawRecord, StagedRecord
    from app.services.staging.confidence import score_extraction
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(RawRecord).where(RawRecord.id == uuid.UUID(raw_record_id))
        )
        raw = result.scalar_one_or_none()
        if raw is None:
            return {"error": "RawRecord not found"}

        payload = raw.raw_payload or {}
        source = raw.source_system

        # Determine record_type from source and payload shape
        if source == "quickbooks":
            if "TxnDate" in payload and "Line" in payload:
                record_type = "invoice"
                extracted = {
                    "invoice_number": payload.get("DocNumber"),
                    "invoice_date": payload.get("TxnDate"),
                    "due_date": payload.get("DueDate"),
                    "amount": payload.get("TotalAmt"),
                    "customer_id": None,  # Needs fuzzy match
                    "qb_invoice_id": payload.get("Id"),
                    "line_items": payload.get("Line", []),
                }
            else:
                record_type = "customer"
                extracted = {
                    "name": payload.get("DisplayName") or payload.get("CompanyName"),
                    "qb_customer_id": payload.get("Id"),
                    "customer_type": "commercial",
                }
        elif source == "bank_csv":
            record_type = "payment"
            extracted = {
                "amount": payload.get("amount"),
                "payment_date": payload.get("date"),
                "reference_number": payload.get("reference") or payload.get("memo"),
                "payment_method": "bank_transfer",
            }
        elif source == "payroll":
            record_type = "labor_shift"
            extracted = {
                "employee_id": payload.get("employee_id"),
                "employee_name": payload.get("employee_name"),
                "shift_date": payload.get("date"),
                "hours_worked": payload.get("hours"),
                "hourly_rate": payload.get("rate"),
                "worker_type": "W2",
            }
        else:
            record_type = "customer"
            extracted = payload

        # Run confidence scoring
        confidence_result = score_extraction(
            record_type=record_type,
            extracted_data=extracted,
            match_suggestions=[],
            source_system=source,
        )
        overall_confidence = confidence_result["overall"]

        # Determine status
        auto_threshold = settings.AGENT_CONFIDENCE_AUTO_APPROVE
        review_threshold = settings.AGENT_CONFIDENCE_NEEDS_REVIEW

        if overall_confidence >= auto_threshold:
            status = "auto_approved"
            auto_approved_at = datetime.now(timezone.utc)
            auto_rule = f"confidence>={auto_threshold}"
        elif overall_confidence >= review_threshold:
            status = "needs_review"
            auto_approved_at = None
            auto_rule = None
        else:
            status = "pending"
            auto_approved_at = None
            auto_rule = None

        staged = StagedRecord(
            id=uuid.uuid4(),
            raw_record_id=raw.id,
            record_type=record_type,
            extracted_data=extracted,
            confidence_score=overall_confidence,
            confidence_reasons=confidence_result["reasons"],
            match_suggestions=[],
            status=status,
            auto_approved_at=auto_approved_at,
            auto_approval_rule=auto_rule,
        )
        session.add(staged)
        await session.commit()

        return {
            "raw_record_id": raw_record_id,
            "staged_record_id": str(staged.id),
            "record_type": record_type,
            "confidence": overall_confidence,
            "status": status,
        }
