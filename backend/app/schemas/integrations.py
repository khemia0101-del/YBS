from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class IntegrationStatus(BaseModel):
    provider: str
    connected: bool
    last_sync_at: datetime | None = None
    last_sync_status: str | None = None
    records_ingested_last_run: int | None = None


class ExchangeRequest(BaseModel):
    """OAuth exchange payload — fields used depend on the provider."""

    public_token: str | None = None  # plaid
    code: str | None = None  # quickbooks / gmail
    realm_id: str | None = None  # quickbooks
