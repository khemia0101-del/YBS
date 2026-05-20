"""Celery dispatcher for OpsLoops."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from app.workers.celery_app import app as celery_app


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.workers.ops_loop_tasks.dispatch_ops_loops")
def dispatch_ops_loops() -> dict:
    """
    Tick task. Scans active OpsLoops; for each whose cron expression is due
    within the dispatcher's tick window (5 minutes), kicks off one run.
    """
    return _run(_dispatch_async())


async def _dispatch_async() -> dict:
    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app.models.ops_loop import OpsLoop
    from app.services.ops_loops.runner import run_loop

    try:
        from croniter import croniter  # type: ignore[import-not-found]
    except ImportError:
        return {"status": "skipped", "reason": "croniter not installed"}

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=5)
    fired: list[str] = []

    async with AsyncSessionLocal() as db:
        loops = (
            await db.execute(select(OpsLoop).where(OpsLoop.is_active.is_(True)))
        ).scalars().all()
        for loop in loops:
            try:
                # Has the cron expression fired since window_start?
                itr = croniter(loop.schedule_cron, window_start)
                next_fire = itr.get_next(datetime)
                if next_fire > now:
                    continue
                # Don't re-fire if the loop already ran since window_start.
                if loop.last_run_at and loop.last_run_at >= window_start:
                    continue
            except Exception:
                continue
            await run_loop(db, loop.id)
            fired.append(str(loop.id))
        await db.commit()

    return {"fired": fired, "scanned": len(loops)}
