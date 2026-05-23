"""Continuous ops loops (Phase 12) — runner + LLM-free fallback."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.models.coo import CooAction
from app.models.ops_loop import OpsLoop, OpsLoopRun
from app.services.ops_loops.runner import run_loop


@pytest.mark.asyncio
async def test_run_loop_without_llm_records_briefing(db_session, sample_company):
    loop = OpsLoop(
        id=uuid.uuid4(),
        company_id=sample_company.id,
        name="Weekly metrics review",
        focus="metrics",
        prompt="Review KPI movements and propose follow-ups.",
        schedule_cron="0 9 * * 1",
        is_active=True,
    )
    db_session.add(loop)
    await db_session.flush()

    run = await run_loop(db_session, loop.id)
    assert run.status == "succeeded"
    assert run.proposed_actions_count == 0  # no LLM, no actions
    assert run.findings_summary is not None
    assert "AI not configured" in run.findings_summary

    # last_run_at gets stamped on the loop.
    refreshed = await db_session.get(OpsLoop, loop.id)
    assert refreshed.last_run_at is not None


@pytest.mark.asyncio
async def test_run_loop_persists_run_row(db_session, sample_company):
    loop = OpsLoop(
        id=uuid.uuid4(),
        company_id=sample_company.id,
        name="Daily cash watch",
        focus="cash",
        prompt="Watch the cash position and propose actions if it dips.",
        schedule_cron="0 7 * * *",
        is_active=True,
    )
    db_session.add(loop)
    await db_session.flush()

    await run_loop(db_session, loop.id)
    rows = (
        await db_session.execute(
            select(OpsLoopRun).where(OpsLoopRun.loop_id == loop.id)
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].ended_at is not None


@pytest.mark.asyncio
async def test_run_loop_with_mocked_llm_creates_coo_actions(
    db_session, sample_company, monkeypatch
):
    loop = OpsLoop(
        id=uuid.uuid4(),
        company_id=sample_company.id,
        name="Funnel review",
        focus="funnel",
        prompt="Look at the funnel and propose actions.",
        schedule_cron="0 9 * * 1",
        is_active=True,
    )
    db_session.add(loop)
    await db_session.flush()

    async def fake_complete(*_args, **_kwargs):
        return {
            "text": "- Sign-ups down 18% WoW. Trial-to-paid steady at 22%.",
            "tool_use": [
                {
                    "id": "a",
                    "name": "assign_employee_task",
                    "input": {
                        "title": "Investigate ad spend",
                        "description": "Pull GA + ad spend by channel.",
                    },
                }
            ],
            "stop_reason": "end_turn",
        }

    monkeypatch.setattr(
        "app.services.ai.llm_client.is_available", lambda: True
    )
    monkeypatch.setattr(
        "app.services.ai.llm_client.complete", fake_complete
    )

    run = await run_loop(db_session, loop.id)
    assert run.status == "succeeded"
    assert run.proposed_actions_count == 1

    actions = (
        await db_session.execute(
            select(CooAction).where(CooAction.company_id == sample_company.id)
        )
    ).scalars().all()
    assert len(actions) == 1
    assert actions[0].action_type == "employee_task"
    assert actions[0].status == "pending"


@pytest.mark.asyncio
async def test_run_loop_raises_for_unknown_id(db_session):
    with pytest.raises(ValueError):
        await run_loop(db_session, uuid.uuid4())
