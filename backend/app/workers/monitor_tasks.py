"""Celery tasks for the self-improving monitor."""
from __future__ import annotations

import asyncio

from app.workers.celery_app import app as celery_app


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.workers.monitor_tasks.run_monitor_loop")
def run_monitor_loop() -> dict:
    """Periodic: collect observations, diagnose each new one, run a reviewer pass."""
    return _run(_run_monitor_loop_async())


async def _run_monitor_loop_async() -> dict:
    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app.models.monitor import AgentObservation
    from app.services.monitor.agent import diagnose
    from app.services.monitor.collectors import run_all_collectors
    from app.services.monitor.reviewer import review

    async with AsyncSessionLocal() as db:
        counts = await run_all_collectors(db)
        await db.commit()
        new_obs = (
            await db.execute(
                select(AgentObservation).where(AgentObservation.status == "new")
            )
        ).scalars().all()
        diagnosed = 0
        for obs in new_obs:
            diag = await diagnose(db, obs.id)
            if diag is not None:
                await review(db, diag.id)
                diagnosed += 1
        await db.commit()
    return {"observations_collected": counts, "diagnoses_drafted": diagnosed}
