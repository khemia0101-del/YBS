"""Automation roadmap tests."""
from __future__ import annotations

import uuid

import pytest

from app.models.interview import InterviewInsight, InterviewSession
from app.services.automation.roadmap import build_roadmap, score


def test_score_favors_high_impact_low_effort():
    assert score("high", "low") > score("high", "high")
    assert score("high", "low") > score("low", "low")
    assert score("high", "low") == 5  # 3*2 - 1


async def _add_automation_insight(db, company_id, title, impact, effort):
    session = InterviewSession(
        id=uuid.uuid4(),
        company_id=company_id,
        role="owner",
        purpose="operations",
        status="completed",
    )
    db.add(session)
    await db.flush()
    db.add(
        InterviewInsight(
            id=uuid.uuid4(),
            session_id=session.id,
            company_id=company_id,
            insight_type="automation_opportunity",
            title=title,
            content={"detail": "From interview.", "impact": impact, "effort": effort},
        )
    )
    await db.flush()


@pytest.mark.asyncio
async def test_build_roadmap_from_interview_insight(db_session, sample_company):
    await _add_automation_insight(
        db_session, sample_company.id, "Automate dispute letters", "high", "low"
    )
    items = await build_roadmap(db_session, sample_company.id)

    match = [i for i in items if i.title == "Automate dispute letters"]
    assert len(match) == 1
    assert match[0].source == "interview"
    assert match[0].priority_score == 5
    assert match[0].status == "proposed"


@pytest.mark.asyncio
async def test_build_roadmap_is_idempotent(db_session, sample_company):
    await _add_automation_insight(
        db_session, sample_company.id, "Automate intake", "medium", "medium"
    )
    first = await build_roadmap(db_session, sample_company.id)
    second = await build_roadmap(db_session, sample_company.id)

    titles_first = [i.title for i in first]
    titles_second = [i.title for i in second]
    assert titles_first == titles_second
    assert titles_second.count("Automate intake") == 1


@pytest.mark.asyncio
async def test_build_roadmap_ranks_by_priority(db_session, sample_company):
    await _add_automation_insight(
        db_session, sample_company.id, "High value quick win", "high", "low"
    )
    await _add_automation_insight(
        db_session, sample_company.id, "Low value slog", "low", "high"
    )
    items = await build_roadmap(db_session, sample_company.id)
    assert items[0].title == "High value quick win"
    assert items[0].priority_score >= items[-1].priority_score
