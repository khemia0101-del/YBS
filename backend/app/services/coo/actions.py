"""Execution of approved COO actions."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coo import CooAction, EmployeeMessage, EmployeeTask
from app.services.notifications.sender import send_email


async def execute_action(db: AsyncSession, action: CooAction) -> dict:
    """
    Execute an approved CooAction and record its outcome. Sets ``action.status``
    and ``action.result``; returns the result dict.
    """
    payload = action.payload or {}

    if action.action_type == "employee_email":
        result = await send_email(
            payload.get("to_email", ""),
            payload.get("subject", ""),
            payload.get("body", ""),
        )
        db.add(
            EmployeeMessage(
                id=uuid.uuid4(),
                company_id=action.company_id,
                to_email=payload.get("to_email", ""),
                subject=payload.get("subject", ""),
                body=payload.get("body", ""),
                status=result["status"],
                source_action_id=action.id,
            )
        )
        action.status = "executed" if result["status"] != "failed" else "failed"
        action.result = result

    elif action.action_type == "employee_task":
        db.add(
            EmployeeTask(
                id=uuid.uuid4(),
                company_id=action.company_id,
                title=payload.get("title", "Task"),
                description=payload.get("description"),
                assignee_name=payload.get("assignee_name"),
                assignee_email=payload.get("assignee_email"),
                status="open",
                source_action_id=action.id,
            )
        )
        action.status = "executed"
        action.result = {"status": "task_created"}

    else:  # business_change — recorded for the owner, nothing to dispatch
        action.status = "executed"
        action.result = {"status": "recorded"}

    await db.flush()
    return action.result
