from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.config import settings

app = Celery(
    "ybs_os",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

app.config_from_object(
    {
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        "timezone": "UTC",
        "enable_utc": True,
        "task_track_started": True,
        "task_acks_late": True,  # Only ack after task finishes (safer with retries)
        "worker_prefetch_multiplier": 1,  # Prevents over-fetching
        "beat_schedule": {
            "daily-hermes-loop": {
                "task": "app.workers.agent_tasks.hermes_daily_loop",
                "schedule": crontab(hour=6, minute=0),
            },
            "weekly-profitability-run": {
                "task": "app.workers.financial_tasks.run_weekly_profitability",
                "schedule": crontab(day_of_week=6, hour=4, minute=0),
            },
            "daily-dso-snapshot": {
                "task": "app.workers.financial_tasks.run_daily_dso",
                "schedule": crontab(hour=7, minute=0),
            },
        },
    }
)

# Auto-discover tasks in workers package
app.autodiscover_tasks(["app.workers"])
