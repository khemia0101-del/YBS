"""
AI COO conversation engine.

Builds a live business-context briefing, then asks Claude to respond as an
executive assistant. Claude may call action tools — those never execute
directly; each becomes a pending CooAction for the owner to approve.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.automation import AutomationItem
from app.models.esop import QoERun
from app.models.profit import ProfitRecommendation
from app.services.ai import llm_client
from app.services.metrics.engine import build_kpi_summary

COO_SYSTEM = """You are the AI COO of a small business — a sharp, plain-spoken \
executive assistant to the owner. You have a live briefing of the business below.

How to behave:
- Answer using the real numbers in the briefing. If something isn't in the briefing, \
say so rather than guessing.
- Be concise and direct, like a good operator. Lead with the answer.
- You can propose actions via your tools, but you NEVER act on your own — every tool \
call becomes a proposal the owner must approve with one tap. Tell the owner plainly \
what you're proposing and why.
- Only propose an action when it clearly helps and the owner would expect it."""

ACTION_TOOLS = [
    {
        "name": "send_employee_email",
        "description": (
            "Draft an email to an employee. It will NOT be sent until the owner "
            "approves it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "to_email": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["to_email", "subject", "body"],
        },
    },
    {
        "name": "assign_employee_task",
        "description": (
            "Assign a task to an employee. It will NOT be assigned until the owner "
            "approves it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "assignee_name": {"type": "string"},
                "assignee_email": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["title", "description"],
        },
    },
    {
        "name": "propose_business_change",
        "description": (
            "Propose an operational or strategic change. Recorded for the owner's "
            "approval; nothing executes automatically."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["title", "description"],
        },
    },
]

_TOOL_TO_ACTION = {
    "send_employee_email": "employee_email",
    "assign_employee_task": "employee_task",
    "propose_business_change": "business_change",
}


async def build_context(db: AsyncSession, company_id: UUID) -> str:
    """Assemble a compact, live business briefing for the COO."""
    lines: list[str] = []

    kpis = await build_kpi_summary(db, company_id, history_limit=2)
    if kpis:
        lines.append("KPIs:")
        for k in kpis:
            cur = k["current_value"] or "n/a"
            chg = f" ({k['change_pct']}% MoM)" if k["change_pct"] else ""
            star = " [north star]" if k["is_north_star"] else ""
            lines.append(f"  - {k['name']}: {cur}{chg}{star}")

    qoe_result = await db.execute(
        select(QoERun)
        .where(QoERun.company_id == company_id)
        .order_by(QoERun.run_date.desc())
        .limit(1)
    )
    run = qoe_result.scalar_one_or_none()
    if run is not None:
        lines.append(
            f"QoE: reported EBITDA {run.reported_ebitda}, adjusted EBITDA "
            f"{run.adjusted_ebitda}, SDE {run.normalized_ebitda}."
        )

    auto_count = await db.execute(
        select(func.count(AutomationItem.id)).where(
            AutomationItem.company_id == company_id,
            AutomationItem.status == "proposed",
        )
    )
    lines.append(f"Open automation opportunities: {auto_count.scalar() or 0}")

    profit_result = await db.execute(
        select(ProfitRecommendation)
        .where(ProfitRecommendation.company_id == company_id)
        .order_by(
            func.coalesce(ProfitRecommendation.estimated_annual_impact, 0).desc()
        )
        .limit(3)
    )
    recs = profit_result.scalars().all()
    if recs:
        lines.append("Top profit recommendations:")
        for r in recs:
            impact = (
                f"${r.estimated_annual_impact:,.0f}/yr"
                if r.estimated_annual_impact is not None
                else "impact TBD"
            )
            lines.append(f"  - {r.title} ({impact})")

    return "\n".join(lines) if lines else "No business data has been loaded yet."


async def converse(
    db: AsyncSession,
    company_id: UUID,
    history: list[dict],
    user_message: str,
) -> dict:
    """
    Produce the COO's reply. Returns ``{"reply", "proposed_actions"}`` where each
    proposed action is ``{"action_type", "title", "payload"}``.
    """
    context = await build_context(db, company_id)

    if not llm_client.is_available():
        return {
            "reply": (
                "The AI COO needs an Anthropic API key (ANTHROPIC_API_KEY) to hold a "
                "conversation. Here is the current business briefing:\n\n" + context
            ),
            "proposed_actions": [],
        }

    system = f"{COO_SYSTEM}\n\n# Live business briefing\n{context}"
    messages = [
        {"role": m["role"], "content": m["content"]} for m in history
    ] + [{"role": "user", "content": user_message}]

    result = await llm_client.complete(
        system, messages, max_tokens=1200, tools=ACTION_TOOLS
    )

    proposed: list[dict] = []
    for tu in result["tool_use"]:
        action_type = _TOOL_TO_ACTION.get(tu["name"])
        if action_type is None:
            continue
        payload = tu["input"]
        if action_type == "employee_email":
            title = f"Email: {payload.get('subject', '(no subject)')}"
        elif action_type == "employee_task":
            title = f"Task: {payload.get('title', '(untitled)')}"
        else:
            title = payload.get("title", "Proposed change")
        proposed.append(
            {"action_type": action_type, "title": title, "payload": payload}
        )

    reply = result["text"].strip()
    if proposed and not reply:
        reply = f"I've prepared {len(proposed)} action(s) for your approval."
    elif proposed:
        reply += (
            f"\n\nI've queued {len(proposed)} action(s) for your approval — "
            "nothing goes out until you approve it."
        )
    return {"reply": reply, "proposed_actions": proposed}
