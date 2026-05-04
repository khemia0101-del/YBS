from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial import DSOSnapshot
from app.models.transactions import Invoice
from app.utils.money import to_money


async def compute_dso(
    session: AsyncSession,
    company_id: uuid.UUID,
    as_of_date: date,
) -> DSOSnapshot:
    """
    Compute Days Sales Outstanding and aging buckets.

    DSO = (total open AR / revenue in trailing 90 days) * 90

    Aging buckets by days_outstanding on open invoices:
      0-30, 31-60, 61-90, 91+
    """
    # Total open AR = sum of (amount - amount_paid) for non-paid invoices
    open_inv_result = await session.execute(
        select(
            Invoice.invoice_date,
            Invoice.due_date,
            Invoice.amount,
            Invoice.amount_paid,
            Invoice.status,
        ).where(
            Invoice.company_id == company_id,
            Invoice.status.in_(["open", "partial", "overdue", "disputed"]),
        )
    )
    open_invoices = open_inv_result.all()

    total_ar = Decimal("0")
    aging_0_30 = Decimal("0")
    aging_31_60 = Decimal("0")
    aging_61_90 = Decimal("0")
    aging_91_plus = Decimal("0")

    for inv in open_invoices:
        balance = to_money((inv.amount or Decimal("0")) - (inv.amount_paid or Decimal("0")))
        if balance <= 0:
            continue
        total_ar += balance

        # Days outstanding from invoice_date
        days = (as_of_date - inv.invoice_date).days
        if days <= 30:
            aging_0_30 += balance
        elif days <= 60:
            aging_31_60 += balance
        elif days <= 90:
            aging_61_90 += balance
        else:
            aging_91_plus += balance

    # Revenue in trailing 90 days (all invoiced amounts, not just collected)
    trailing_start = as_of_date - timedelta(days=90)
    rev_result = await session.execute(
        select(func.sum(Invoice.amount)).where(
            Invoice.company_id == company_id,
            Invoice.invoice_date >= trailing_start,
            Invoice.invoice_date <= as_of_date,
            Invoice.status != "void",
        )
    )
    trailing_revenue = to_money(rev_result.scalar() or Decimal("0"))

    # Avoid division by zero
    if trailing_revenue > 0:
        avg_daily_revenue = to_money(trailing_revenue / 90)
        dso_days = to_money(total_ar / avg_daily_revenue) if avg_daily_revenue > 0 else Decimal("0")
    else:
        avg_daily_revenue = Decimal("0")
        dso_days = Decimal("0")

    snap = DSOSnapshot(
        id=uuid.uuid4(),
        company_id=company_id,
        snapshot_date=as_of_date,
        dso_days=dso_days,
        total_ar=to_money(total_ar),
        avg_daily_revenue=avg_daily_revenue,
        aging_0_30=to_money(aging_0_30),
        aging_31_60=to_money(aging_31_60),
        aging_61_90=to_money(aging_61_90),
        aging_91_plus=to_money(aging_91_plus),
        calculation_version="v1.0.0",
    )
    session.add(snap)
    await session.flush()
    return snap
