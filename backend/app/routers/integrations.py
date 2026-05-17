"""Per-business integration connections — connect, sync, disconnect.

OAuth uses the SPA pattern: ``/authorize`` returns the provider URL; the provider
redirects to a frontend route which then calls the authenticated ``/exchange``
endpoint with the returned code. No unauthenticated callback is exposed.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import assert_company_in_tenant, get_tenant_id, require_operator
from app.models.sync import SyncLog
from app.models.users import User
from app.schemas.integrations import ExchangeRequest, IntegrationStatus
from app.services.integrations import CONNECTORS, IntegrationError, get_connector
from app.services.integrations.gmail_connector import GmailConnector
from app.services.integrations.plaid_connector import PlaidConnector
from app.services.integrations.quickbooks_connector import QuickBooksConnector

router = APIRouter()


@router.get("", response_model=list[IntegrationStatus])
async def list_integrations(
    company_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> list[IntegrationStatus]:
    await assert_company_in_tenant(db, company_id, tenant_id)
    statuses: list[IntegrationStatus] = []
    for provider in CONNECTORS:
        connector = get_connector(provider, company_id)
        connected = await connector.is_connected(db)
        log_result = await db.execute(
            select(SyncLog)
            .where(SyncLog.company_id == company_id, SyncLog.source_system == provider)
            .order_by(SyncLog.started_at.desc())
            .limit(1)
        )
        log = log_result.scalar_one_or_none()
        statuses.append(
            IntegrationStatus(
                provider=provider,
                connected=connected,
                last_sync_at=log.started_at if log else None,
                last_sync_status=log.status if log else None,
                records_ingested_last_run=log.records_ingested if log else None,
            )
        )
    return statuses


@router.get("/{provider}/authorize")
async def authorize(
    provider: str,
    company_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user: User = Depends(require_operator),
) -> dict:
    """Return the provider OAuth URL. ``state`` carries the company id."""
    await assert_company_in_tenant(db, company_id, tenant_id)
    state = str(company_id)
    try:
        if provider == "quickbooks":
            return {"authorize_url": QuickBooksConnector.authorize_url(state)}
        if provider == "gmail":
            return {"authorize_url": GmailConnector.authorize_url(state)}
    except IntegrationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    raise HTTPException(
        status_code=400,
        detail=f"'{provider}' does not use an authorize URL (Plaid uses /link-token).",
    )


@router.post("/plaid/link-token")
async def plaid_link_token(
    company_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user: User = Depends(require_operator),
) -> dict:
    await assert_company_in_tenant(db, company_id, tenant_id)
    try:
        token = await PlaidConnector(company_id).create_link_token()
    except IntegrationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"link_token": token}


@router.post("/{provider}/exchange")
async def exchange(
    provider: str,
    body: ExchangeRequest,
    company_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user: User = Depends(require_operator),
) -> dict:
    """Complete the OAuth flow and store encrypted credentials for the business."""
    await assert_company_in_tenant(db, company_id, tenant_id)
    try:
        if provider == "plaid":
            if not body.public_token:
                raise HTTPException(status_code=400, detail="public_token is required")
            result = await PlaidConnector(company_id).exchange_public_token(
                db, body.public_token
            )
        elif provider == "quickbooks":
            if not body.code or not body.realm_id:
                raise HTTPException(
                    status_code=400, detail="code and realm_id are required"
                )
            result = await QuickBooksConnector(company_id).exchange_code(
                db, body.code, body.realm_id
            )
        elif provider == "gmail":
            if not body.code:
                raise HTTPException(status_code=400, detail="code is required")
            result = await GmailConnector(company_id).exchange_code(db, body.code)
        else:
            raise HTTPException(status_code=404, detail=f"Unknown provider '{provider}'")
    except IntegrationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"provider": provider, "connected": True, **result}


@router.post("/{provider}/sync")
async def trigger_sync(
    provider: str,
    company_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user: User = Depends(require_operator),
) -> dict:
    """Run a sync now. Enqueues a Celery task; falls back to inline on failure."""
    await assert_company_in_tenant(db, company_id, tenant_id)
    if provider not in CONNECTORS:
        raise HTTPException(status_code=404, detail=f"Unknown provider '{provider}'")
    try:
        from app.workers.integration_tasks import sync_integration

        task = sync_integration.delay(str(company_id), provider)
        return {"provider": provider, "status": "queued", "task_id": task.id}
    except Exception:
        connector = get_connector(provider, company_id)
        try:
            result = await connector.sync(db)
        except IntegrationError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {"provider": provider, "status": "completed", **result}


@router.delete("/{provider}")
async def disconnect(
    provider: str,
    company_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user: User = Depends(require_operator),
) -> dict:
    await assert_company_in_tenant(db, company_id, tenant_id)
    if provider not in CONNECTORS:
        raise HTTPException(status_code=404, detail=f"Unknown provider '{provider}'")
    removed = await get_connector(provider, company_id).disconnect(db)
    return {"provider": provider, "disconnected": removed}
