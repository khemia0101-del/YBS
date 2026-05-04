from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial import CashForecastRun, CashForecastWeek
from app.models.transactions import Invoice
from app.utils.money import to_money

# Collection probability by days outstanding bucket
COLLECTION_PROB = {
    "0_30": Decimal("0.95"),
    "31_60": Decimal("0.80"),
    "61_90": Decimal("0.60"),
    "91_plus": Decimal("0.30"),
}

# Multipliers for forecast modes
MODE_MULTIPLIERS = {
    "baseline": Decimal("1.00"),
    "optimistic": Decimal("1.10"),
    "stress": Decimal("0.80"),
}


def _week_start(base: date, week_num: int) -> date:
    """Return the Monday of week_num (1-indexed) starting from base."""
    # Advance to next Monday from base
    days_to_monday = (7 - base.weekday()) % 7
    first_monday = base + timedelta(days=days_to_monday if days_to_monday > 0 else 7)
    return first_monday + timedelta(weeks=week_num - 1)


def _collection_prob_for_days(days_outstanding: int) -> Decimal:
    if days_outstanding <= 30:
        return COLLECTION_PROB["0_30"]
    elif days_outstanding <= 60:
        return COLLECTION_PROB["31_60"]
    elif days_outstanding <= 90:
        return COLLECTION_PROB["61_90"]
    return COLLECTION_PROB["91_plus"]


async def build_13_week_forecast(
    session: AsyncSession,
    company_id: UUID,
    beginning_cash: Decimal,
    mode: str = "baseline",
    run_by: UUID | None = None,
) -> UUID:
    """
    Build a 13-week cash flow forecast.

    AR collections per week are estimated by:
    - Bucketing open invoices by their expected collection week
    - Applying collection probability based on days outstanding
    - Scaling by mode multiplier

    Payroll outflow is approximated as:
    - Bi-weekly payroll = last 4-week labor cost / 2, on weeks 2 and 4 pattern

    Returns the CashForecastRun.id.
    """
    today = date.today()
    mode_mult = MODE_MULTIPLIERS.get(mode, Decimal("1.00"))

    # Fetch open invoices
    open_inv_result = await session.execute(
        select(
            Invoice.id,
            Invoice.due_date,
            Invoice.invoice_date,
            Invoice.amount,
            Invoice.amount_paid,
            Invoice.days_outstanding,
        ).where(
            Invoice.company_id == company_id,
            Invoice.status.in_(["open", "partial", "overdue"]),
        )
    )
    open_invoices = open_inv_result.all()

    # Estimate weekly payroll from labor burden (simplified average)
    from app.models.transactions import LaborShift

    labor_result = await session.execute(
        select(func.sum(LaborShift.labor_cost)).where(
            LaborShift.company_id == company_id,
            LaborShift.shift_date >= today - timedelta(days=28),
            LaborShift.shift_date < today,
        )
    )
    last_4wk_labor = to_money(labor_result.scalar() or Decimal("0"))
    weekly_payroll_estimate = to_money(last_4wk_labor / 4)

    # Estimate weekly overhead = 10% of AR collections estimate (simplified)
    # We'll compute it per-week dynamically below

    # Create forecast run
    run = CashForecastRun(
        id=uuid.uuid4(),
        company_id=company_id,
        run_date=today,
        forecast_start=today,
        forecast_weeks=13,
        mode=mode,
        beginning_cash=to_money(beginning_cash),
        status="draft",
        approved_by=run_by,
    )
    session.add(run)
    await session.flush()

    current_cash = to_money(beginning_cash)
    min_cash = current_cash
    min_cash_week = 1
    last_payroll_week = 0  # track bi-weekly payroll

    for week_num in range(1, 14):
        wk_start = _week_start(today, week_num)
        wk_end = wk_start + timedelta(days=6)

        # AR collections: invoices due this week * collection_prob
        ar_collections = Decimal("0")
        for inv in open_invoices:
            balance = to_money((inv.amount or Decimal("0")) - (inv.amount_paid or Decimal("0")))
            if balance <= 0:
                continue
            days_out = inv.days_outstanding or (today - inv.invoice_date).days
            prob = _collection_prob_for_days(days_out)
            # Weight by whether due_date falls in this week
            if inv.due_date and wk_start <= inv.due_date <= wk_end:
                ar_collections += to_money(balance * prob * mode_mult)
            else:
                # Distribute remaining collections evenly over weeks proportionally
                ar_collections += to_money(balance * prob * mode_mult / 13)

        ar_collections = to_money(ar_collections)

        # Payroll: bi-weekly on weeks 2, 4, 6, 8, 10, 12
        payroll_outflow = Decimal("0")
        if week_num % 2 == 0:
            payroll_outflow = to_money(weekly_payroll_estimate * 2)
        elif week_num == 1:
            payroll_outflow = weekly_payroll_estimate  # First week may have partial

        # Overhead: fixed estimate at 15% of revenue
        overhead_outflow = to_money(ar_collections * Decimal("0.10"))

        net_flow = to_money(ar_collections - payroll_outflow - overhead_outflow)
        ending = to_money(current_cash + net_flow)

        if ending < min_cash:
            min_cash = ending
            min_cash_week = week_num

        week = CashForecastWeek(
            id=uuid.uuid4(),
            run_id=run.id,
            week_number=week_num,
            week_start=wk_start,
            beginning_cash=current_cash,
            ar_collections=ar_collections,
            other_inflows=Decimal("0"),
            payroll_outflow=payroll_outflow,
            subcontractor_outflow=Decimal("0"),
            overhead_outflow=overhead_outflow,
            other_outflows=Decimal("0"),
            net_cash_flow=net_flow,
            ending_cash=ending,
        )
        session.add(week)
        current_cash = ending

    # Estimate payroll coverage — how many weeks until cash goes below bi-weekly payroll
    payroll_covered_through: date | None = None
    # Find the week after which ending_cash < one payroll cycle
    payroll_covered_through = _week_start(today, 13) + timedelta(days=6)  # Conservative: full 13 wks

    run.ending_cash = to_money(current_cash)
    run.min_cash_amount = min_cash
    run.min_cash_week = min_cash_week
    run.payroll_covered_through = payroll_covered_through
    run.status = "completed"

    await session.flush()
    return run.id
