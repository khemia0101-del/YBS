"""AI COO tests — exercise context, fallback, and action execution (no LLM/SendGrid)."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.models.coo import CooAction, EmployeeMessage, EmployeeTask
from app.services.coo.actions import execute_action
from app.services.coo.assistant import build_context, converse
from app.services.notifications.sender import send_email


@pytest.mark.asyncio
async def test_send_email_skipped_without_config():
    result = await send_email("a@b.com", "Hi", "Body")
    assert result["status"] == "skipped"


@pytest.mark.asyncio
async def test_build_context_returns_text(db_session, sample_company):
    ctx = await build_context(db_session, sample_company.id)
    assert isinstance(ctx, str)
    assert len(ctx) > 0


@pytest.mark.asyncio
async def test_converse_without_api_key_returns_briefing(db_session, sample_company):
    out = await converse(db_session, sample_company.id, [], "How are we doing?")
    assert out["proposed_actions"] == []
    assert "ANTHROPIC_API_KEY" in out["reply"]


@pytest.mark.asyncio
async def test_execute_employee_task_action(db_session, sample_company):
    action = CooAction(
        id=uuid.uuid4(),
        company_id=sample_company.id,
        action_type="employee_task",
        title="Task: Call client",
        payload={
            "title": "Call client",
            "description": "Follow up",
            "assignee_name": "Sam",
        },
        status="approved",
    )
    db_session.add(action)
    await db_session.flush()

    await execute_action(db_session, action)
    assert action.status == "executed"

    rows = (
        await db_session.execute(
            select(EmployeeTask).where(EmployeeTask.company_id == sample_company.id)
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].title == "Call client"
    assert rows[0].status == "open"


@pytest.mark.asyncio
async def test_execute_employee_email_action_logs_message(db_session, sample_company):
    action = CooAction(
        id=uuid.uuid4(),
        company_id=sample_company.id,
        action_type="employee_email",
        title="Email: Update",
        payload={"to_email": "e@co.com", "subject": "Update", "body": "Hello"},
        status="approved",
    )
    db_session.add(action)
    await db_session.flush()

    await execute_action(db_session, action)
    # No SendGrid key -> email skipped, but the action completes and is logged.
    assert action.status == "executed"
    msgs = (
        await db_session.execute(
            select(EmployeeMessage).where(
                EmployeeMessage.company_id == sample_company.id
            )
        )
    ).scalars().all()
    assert len(msgs) == 1
    assert msgs[0].to_email == "e@co.com"


@pytest.mark.asyncio
async def test_execute_business_change_action(db_session, sample_company):
    action = CooAction(
        id=uuid.uuid4(),
        company_id=sample_company.id,
        action_type="business_change",
        title="Raise prices",
        payload={"title": "Raise prices", "description": "+5%"},
        status="approved",
    )
    db_session.add(action)
    await db_session.flush()

    result = await execute_action(db_session, action)
    assert action.status == "executed"
    assert result["status"] == "recorded"
