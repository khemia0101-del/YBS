"""
Automation roadmap builder.

Merges interview insights and observed data patterns into a ranked, idempotent
automation backlog. Each item is scored by impact and effort; dispatched items
are linked to an AgentTask routed through the existing approval queue.
"""
from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.automation import AutomationItem
from app.models.interview import InterviewInsight
from app.models.raw import RawRecord, StagedRecord

_WEIGHT = {"low": 1, "medium": 2, "high": 3}


def score(impact: str, effort: str) -> int:
    """Higher is better — favors high impact and low effort."""
    return _WEIGHT.get(impact, 2) * 2 - _WEIGHT.get(effort, 2)


async def _interview_candidates(db: AsyncSession, company_id: UUID) -> list[dict]:
    result = await db.execute(
        select(InterviewInsight).where(
            InterviewInsight.company_id == company_id,
            InterviewInsight.insight_type == "automation_opportunity",
        )
    )
    candidates = []
    for ins in result.scalars().all():
        content = ins.content or {}
        candidates.append(
            {
                "title": ins.title,
                "description": content.get("detail", ""),
                "category": "interview",
                "source": "interview",
                "source_ref": str(ins.session_id),
                "impact": content.get("impact", "medium"),
                "effort": content.get("effort", "medium"),
            }
        )
    return candidates


async def _observed_candidates(db: AsyncSession, company_id: UUID) -> list[dict]:
    candidates: list[dict] = []

    pending = await db.execute(
        select(func.count(StagedRecord.id))
        .join(RawRecord, StagedRecord.raw_record_id == RawRecord.id)
        .where(RawRecord.company_id == company_id, StagedRecord.status == "pending")
    )
    pending_count = pending.scalar() or 0
    if pending_count >= 5:
        candidates.append(
            {
                "title": "Auto-reconcile incoming records",
                "description": (
                    f"{pending_count} staged records are awaiting manual review — "
                    "widen auto-approval coverage to clear routine matches."
                ),
                "category": "data_ops",
                "source": "observed",
                "source_ref": "staged_pending",
                "impact": "high",
                "effort": "medium",
            }
        )

    by_source = await db.execute(
        select(RawRecord.source_system, func.count(RawRecord.id))
        .where(RawRecord.company_id == company_id)
        .group_by(RawRecord.source_system)
    )
    for source_system, count in by_source.all():
        if count >= 20:
            candidates.append(
                {
                    "title": f"Automate {source_system} data handling",
                    "description": (
                        f"{count} {source_system} records have been ingested — codify "
                        "the recurring processing steps into a scheduled task."
                    ),
                    "category": "data_ops",
                    "source": "observed",
                    "source_ref": source_system,
                    "impact": "medium",
                    "effort": "medium",
                }
            )
    return candidates


async def build_roadmap(db: AsyncSession, company_id: UUID) -> list[AutomationItem]:
    """Refresh the company's automation backlog; returns it ranked by priority."""
    candidates = await _interview_candidates(db, company_id)
    candidates += await _observed_candidates(db, company_id)

    existing_result = await db.execute(
        select(AutomationItem).where(AutomationItem.company_id == company_id)
    )
    existing = {i.title: i for i in existing_result.scalars().all()}

    for c in candidates:
        s = score(c["impact"], c["effort"])
        item = existing.get(c["title"])
        if item is None:
            item = AutomationItem(
                id=uuid.uuid4(),
                company_id=company_id,
                title=c["title"],
                description=c["description"],
                category=c["category"],
                source=c["source"],
                source_ref=c["source_ref"],
                impact=c["impact"],
                effort=c["effort"],
                priority_score=s,
                status="proposed",
            )
            db.add(item)
            existing[c["title"]] = item
        elif item.status == "proposed":
            # Refresh still-proposed items; never touch dispatched/done ones.
            item.description = c["description"]
            item.impact = c["impact"]
            item.effort = c["effort"]
            item.priority_score = s
    await db.flush()

    result = await db.execute(
        select(AutomationItem)
        .where(AutomationItem.company_id == company_id)
        .order_by(AutomationItem.priority_score.desc(), AutomationItem.title)
    )
    return list(result.scalars().all())
