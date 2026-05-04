from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timezone

from app.workers.celery_app import app as celery_app


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.workers.agent_tasks.hermes_daily_loop")
def hermes_daily_loop() -> dict:
    """
    Hermes agent daily operations loop.

    Checks:
    1. Sync status — flag stale sources
    2. Exceptions queue — attempt auto-resolution on high-confidence records
    3. Cash position — flag if below threshold
    4. AR aging — flag overdue invoices
    5. Compliance — flag expiring documents
    6. Execute low-risk tasks directly
    7. Draft high-risk actions as ApprovalRequests
    8. Send Telegram summary to operator
    """
    return _run_async(_hermes_loop_async())


async def _hermes_loop_async() -> dict:
    from app.config import settings
    from app.database import AsyncSessionLocal
    from app.models.agent import AgentTask, ApprovalRequest
    from app.models.core import Company
    from app.models.raw import StagedRecord
    from app.models.transactions import Invoice
    from sqlalchemy import func, select
    from sqlalchemy.ext.asyncio import AsyncSession

    summary_lines: list[str] = []
    actions_taken: list[str] = []
    approvals_requested: list[str] = []

    async with AsyncSessionLocal() as session:
        # --- 1. Sync status ---
        from app.models.sync import SyncLog
        from datetime import timedelta

        stale_threshold = datetime.now(timezone.utc) - timedelta(hours=25)
        for source in ["quickbooks", "swept", "payroll"]:
            latest_result = await session.execute(
                select(SyncLog)
                .where(SyncLog.source_system == source, SyncLog.status == "completed")
                .order_by(SyncLog.started_at.desc())
                .limit(1)
            )
            latest = latest_result.scalar_one_or_none()
            if latest is None or latest.started_at < stale_threshold:
                summary_lines.append(f"⚠️ {source} sync stale — last run: {latest.started_at if latest else 'never'}")

        # --- 2. Exceptions queue ---
        pending_result = await session.execute(
            select(func.count(StagedRecord.id)).where(StagedRecord.status == "pending")
        )
        pending_count = pending_result.scalar() or 0
        if pending_count > 0:
            summary_lines.append(f"📋 {pending_count} staged records pending review")

        # Auto-approve high-confidence pending records
        auto_threshold = settings.AGENT_CONFIDENCE_AUTO_APPROVE
        auto_candidates_result = await session.execute(
            select(StagedRecord)
            .where(
                StagedRecord.status == "pending",
                StagedRecord.confidence_score >= auto_threshold,
            )
            .limit(50)
        )
        auto_candidates = auto_candidates_result.scalars().all()

        now = datetime.now(timezone.utc)
        for rec in auto_candidates:
            rec.status = "auto_approved"
            rec.auto_approved_at = now
            rec.auto_approval_rule = f"hermes_daily_loop confidence>={auto_threshold}"
            actions_taken.append(f"auto_approved staged_record {rec.id}")

        if auto_candidates:
            summary_lines.append(f"✅ Auto-approved {len(auto_candidates)} high-confidence records")

        # --- 3. Cash position check ---
        from app.models.financial import CashForecastRun

        cos_result = await session.execute(select(Company.id, Company.legal_name))
        companies = cos_result.all()

        for company_id, company_name in companies:
            latest_forecast = await session.execute(
                select(CashForecastRun)
                .where(CashForecastRun.company_id == company_id)
                .order_by(CashForecastRun.run_date.desc())
                .limit(1)
            )
            forecast = latest_forecast.scalar_one_or_none()
            if forecast and forecast.min_cash_amount is not None:
                if forecast.min_cash_amount < 50000:
                    summary_lines.append(
                        f"🚨 {company_name}: minimum projected cash ${forecast.min_cash_amount:,.2f} "
                        f"in week {forecast.min_cash_week}"
                    )

        # --- 4. AR aging ---
        from sqlalchemy import and_

        overdue_result = await session.execute(
            select(func.count(Invoice.id), func.sum(Invoice.amount - Invoice.amount_paid)).where(
                Invoice.status == "overdue"
            )
        )
        overdue_row = overdue_result.one()
        overdue_count = overdue_row[0] or 0
        overdue_amount = overdue_row[1] or 0
        if overdue_count > 0:
            summary_lines.append(
                f"💸 {overdue_count} overdue invoices totaling ${overdue_amount:,.2f}"
            )

        # --- 5. Compliance documents ---
        from app.models.core import ComplianceDocument

        expiring_soon = date.today() + timedelta(days=30)
        expiring_result = await session.execute(
            select(func.count(ComplianceDocument.id)).where(
                ComplianceDocument.expiry_date <= expiring_soon,
                ComplianceDocument.status == "active",
            )
        )
        expiring_count = expiring_result.scalar() or 0
        if expiring_count > 0:
            summary_lines.append(f"📄 {expiring_count} compliance docs expiring within 30 days")

        # Commit all auto-approvals
        await session.commit()

    # --- 8. Send Telegram summary ---
    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_OPERATOR_CHAT_ID:
        await _send_telegram_summary(summary_lines, actions_taken, approvals_requested)

    return {
        "date": date.today().isoformat(),
        "summary_items": len(summary_lines),
        "actions_taken": len(actions_taken),
        "approvals_requested": len(approvals_requested),
        "summary": summary_lines,
        "actions": actions_taken,
    }


async def _send_telegram_summary(
    summary: list[str], actions: list[str], approvals: list[str]
) -> None:
    from app.config import settings
    import httpx

    msg_parts = ["🤖 *Hermes Daily Loop — " + date.today().isoformat() + "*\n"]

    if summary:
        msg_parts.append("*Status:*")
        msg_parts.extend(summary)
    else:
        msg_parts.append("✅ All systems nominal")

    if actions:
        msg_parts.append(f"\n*Auto-actions ({len(actions)}):*")
        msg_parts.extend(actions[:5])
        if len(actions) > 5:
            msg_parts.append(f"  ...and {len(actions) - 5} more")

    if approvals:
        msg_parts.append(f"\n*Pending Approvals ({len(approvals)}):*")
        msg_parts.extend(approvals[:3])

    message = "\n".join(msg_parts)[:4096]  # Telegram max message length

    try:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                url,
                json={
                    "chat_id": settings.TELEGRAM_OPERATOR_CHAT_ID,
                    "text": message,
                    "parse_mode": "Markdown",
                },
            )
    except Exception:
        pass  # Best-effort notification
