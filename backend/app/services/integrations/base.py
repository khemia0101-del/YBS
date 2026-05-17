"""
Integration connector framework.

Each connector authenticates to a provider (Plaid, QuickBooks, Gmail) via OAuth,
stores tokens encrypted per company, and on ``sync()`` pulls raw items into the
existing ``RawRecord`` ingestion pipeline. Tokens never leave the encrypted vault.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.raw import RawRecord
from app.models.sync import IntegrationCredential, SyncLog
from app.security.encryption import vault


class IntegrationError(Exception):
    """Raised when a connector is misconfigured or a provider call fails."""


class BaseConnector:
    """Common credential storage + sync plumbing for all provider connectors."""

    provider: str = ""

    def __init__(self, company_id: UUID) -> None:
        self.company_id = company_id

    # ── Credential storage (encrypted, per company) ───────────────────────
    async def _active_credential(
        self, db: AsyncSession
    ) -> IntegrationCredential | None:
        result = await db.execute(
            select(IntegrationCredential)
            .where(
                IntegrationCredential.company_id == self.company_id,
                IntegrationCredential.source_system == self.provider,
                IntegrationCredential.is_active.is_(True),
            )
            .order_by(IntegrationCredential.created_at.desc())
        )
        return result.scalars().first()

    async def load_tokens(self, db: AsyncSession) -> dict | None:
        cred = await self._active_credential(db)
        if cred is None:
            return None
        return json.loads(vault.decrypt(cred.encrypted_value))

    async def is_connected(self, db: AsyncSession) -> bool:
        return await self._active_credential(db) is not None

    async def store_tokens(
        self,
        db: AsyncSession,
        tokens: dict,
        metadata: dict | None = None,
        expires_at: datetime | None = None,
    ) -> IntegrationCredential:
        """Encrypt + persist tokens, deactivating any prior credential."""
        prior = await self._active_credential(db)
        if prior is not None:
            prior.is_active = False

        cred = IntegrationCredential(
            id=uuid.uuid4(),
            company_id=self.company_id,
            source_system=self.provider,
            credential_type="oauth_tokens",
            encrypted_value=vault.encrypt(json.dumps(tokens)),
            metadata_json=metadata or {},
            expires_at=expires_at,
            is_active=True,
        )
        db.add(cred)
        await db.flush()
        return cred

    async def disconnect(self, db: AsyncSession) -> bool:
        cred = await self._active_credential(db)
        if cred is None:
            return False
        cred.is_active = False
        await db.flush()
        return True

    # ── Sync ──────────────────────────────────────────────────────────────
    async def fetch(self, db: AsyncSession, since: datetime | None) -> list[dict]:
        """Return raw provider records. Implemented per connector."""
        raise NotImplementedError

    async def sync(self, db: AsyncSession, since: datetime | None = None) -> dict:
        """Run a full sync: fetch provider items, persist as RawRecords, log it."""
        log = SyncLog(
            id=uuid.uuid4(),
            company_id=self.company_id,
            source_system=self.provider,
            status="running",
        )
        db.add(log)
        await db.flush()

        try:
            items = await self.fetch(db, since)
            new_count = await self._persist(db, items)
            log.status = "completed"
            log.ended_at = datetime.now(timezone.utc)
            log.records_ingested = new_count
            await db.flush()
            return {
                "provider": self.provider,
                "fetched": len(items),
                "new": new_count,
            }
        except Exception as exc:
            log.status = "failed"
            log.ended_at = datetime.now(timezone.utc)
            log.errors_json = [str(exc)]
            await db.flush()
            raise

    async def _persist(self, db: AsyncSession, items: list[dict]) -> int:
        """Create company-scoped RawRecords, skipping checksum duplicates."""
        new_count = 0
        for item in items:
            checksum = hashlib.sha256(
                json.dumps(item, sort_keys=True, default=str).encode()
            ).hexdigest()
            existing = await db.execute(
                select(RawRecord.id).where(
                    RawRecord.checksum == checksum,
                    RawRecord.company_id == self.company_id,
                    RawRecord.is_duplicate.is_(False),
                )
            )
            if existing.scalar_one_or_none() is not None:
                continue
            db.add(
                RawRecord(
                    id=uuid.uuid4(),
                    company_id=self.company_id,
                    source_system=self.provider,
                    source_ref=str(item.get("id") or item.get("Id") or ""),
                    raw_payload=item,
                    checksum=checksum,
                    is_duplicate=False,
                )
            )
            new_count += 1
        await db.flush()
        return new_count
