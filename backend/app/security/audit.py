from __future__ import annotations

from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def write_audit_log(
    session: AsyncSession,
    event_type: str,
    actor_id: UUID | None,
    actor_type: Literal["user", "agent", "system"],
    table_name: str | None = None,
    record_id: UUID | None = None,
    before_state: dict | None = None,
    after_state: dict | None = None,
    metadata: dict | None = None,
) -> None:
    """
    Append an immutable audit entry to audit_logs.

    This function ONLY inserts; it never updates or deletes existing records.
    Commit is handled by the caller's session context (e.g. get_db dependency).
    """
    log = AuditLog(
        event_type=event_type,
        actor_id=actor_id,
        actor_type=actor_type,
        table_name=table_name,
        record_id=record_id,
        before_state=before_state,
        after_state=after_state,
        metadata_=metadata,
    )
    session.add(log)
    # Intentionally not committing here — caller owns the transaction.
