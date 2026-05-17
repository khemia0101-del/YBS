"""Celery tasks for scheduled integration syncing."""
from __future__ import annotations

import asyncio
import uuid

from app.workers.celery_app import app as celery_app


def _run_async(coro):
    """Run a coroutine in a fresh event loop (safe inside Celery workers)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=4,
    name="app.workers.integration_tasks.sync_integration",
)
def sync_integration(self, company_id: str, provider: str) -> dict:
    """Sync one provider for one business."""
    try:
        return _run_async(_sync_one(company_id, provider))
    except Exception as exc:
        raise self.retry(exc=exc)


async def _sync_one(company_id: str, provider: str) -> dict:
    from app.database import AsyncSessionLocal
    from app.services.integrations import get_connector

    async with AsyncSessionLocal() as session:
        connector = get_connector(provider, uuid.UUID(company_id))
        result = await connector.sync(session)
        await session.commit()
        return result


@celery_app.task(name="app.workers.integration_tasks.sync_all_integrations")
def sync_all_integrations() -> dict:
    """Find every connected integration and enqueue a per-business sync."""
    return _run_async(_enqueue_all())


async def _enqueue_all() -> dict:
    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app.models.sync import IntegrationCredential

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(
                IntegrationCredential.company_id,
                IntegrationCredential.source_system,
            ).where(IntegrationCredential.is_active.is_(True))
        )
        pairs = {(str(row[0]), row[1]) for row in result.all()}

    for company_id, provider in pairs:
        sync_integration.delay(company_id, provider)
    return {"enqueued": len(pairs)}
