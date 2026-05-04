from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial import (
    LaborBurdenAssumption,
    ProfitabilityRun,
    ProfitabilityRunLine,
)
from app.models.transactions import Invoice, LaborShift
from app.utils.money import to_money


async def _get_active_burden(
    session: AsyncSession, company_id: UUID, as_of: date
) -> LaborBurdenAssumption | None:
    """Fetch the most recent active burden assumption for the company (or global)."""
    result = await session.execute(
        select(LaborBurdenAssumption)
        .where(
            LaborBurdenAssumption.is_active.is_(True),
            LaborBurdenAssumption.effective_date <= as_of,
            (LaborBurdenAssumption.company_id == company_id)
            | (LaborBurdenAssumption.company_id.is_(None)),
        )
        .order_by(
            LaborBurdenAssumption.company_id.desc().nullslast(),
            LaborBurdenAssumption.effective_date.desc(),
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def compute_contract_profitability(
    session: AsyncSession,
    contract_id: UUID,
    period_start: date,
    period_end: date,
    calculation_version: str = "v1.0.0",
    run_id: UUID | None = None,
    company_id: UUID | None = None,
) -> ProfitabilityRunLine:
    """
    Compute contribution margin for a single contract over a period.

    Steps:
    1. Fetch invoices for the contract in the period (= revenue).
    2. Fetch labor shifts for the contract in the period.
    3. Fetch active labor burden assumptions.
    4. Apply burden to W2 labor cost.
    5. Build ProfitabilityRunLine with evidence details.
    """
    # 1. Revenue = sum of invoices in period
    inv_result = await session.execute(
        select(func.sum(Invoice.amount)).where(
            Invoice.contract_id == contract_id,
            Invoice.invoice_date >= period_start,
            Invoice.invoice_date <= period_end,
        )
    )
    revenue = to_money(inv_result.scalar() or Decimal("0"))

    # 2. Labor shifts
    shifts_result = await session.execute(
        select(LaborShift).where(
            LaborShift.contract_id == contract_id,
            LaborShift.shift_date >= period_start,
            LaborShift.shift_date <= period_end,
        )
    )
    shifts = shifts_result.scalars().all()

    w2_base_cost = Decimal("0")
    sub_cost = Decimal("0")
    total_hours = Decimal("0")

    for shift in shifts:
        cost = shift.labor_cost or (
            (shift.hours_worked or Decimal("0")) * (shift.hourly_rate or Decimal("0"))
        )
        cost = to_money(cost)
        if shift.worker_type == "W2":
            w2_base_cost += cost
        else:
            sub_cost += cost
        total_hours += shift.hours_worked or Decimal("0")

    # 3. Burden assumptions
    burden_pct = Decimal("0.30")  # Default fallback
    if company_id:
        burden = await _get_active_burden(session, company_id, period_end)
        if burden:
            burden_pct = burden.total_burden_pct

    # 4. Apply burden
    burden_cost = to_money(w2_base_cost * burden_pct)
    total_direct_labor = to_money(w2_base_cost + burden_cost)

    # 5. Contribution margin
    contribution = to_money(revenue - total_direct_labor - sub_cost)
    margin_pct = (
        to_money(contribution / revenue * 100) if revenue > 0 else Decimal("0")
    )

    # Confidence: high if we have both invoices and shifts, lower if either is missing
    has_revenue = revenue > 0
    has_labor = len(shifts) > 0
    confidence = Decimal("0.90") if (has_revenue and has_labor) else (
        Decimal("0.70") if has_revenue else Decimal("0.50")
    )

    line = ProfitabilityRunLine(
        id=uuid.uuid4(),
        run_id=run_id or uuid.uuid4(),
        contract_id=contract_id,
        customer_id=uuid.uuid4(),  # Will be set by caller
        revenue=revenue,
        direct_labor_cost=to_money(w2_base_cost),
        burden_cost=burden_cost,
        subcontractor_cost=to_money(sub_cost),
        supplies_cost=Decimal("0"),
        contribution_margin=contribution,
        contribution_margin_pct=margin_pct,
        labor_hours=to_money(total_hours),
        confidence_score=confidence,
        calculation_version=calculation_version,
    )
    return line


async def run_company_profitability(
    session: AsyncSession,
    company_id: UUID,
    period_start: date,
    period_end: date,
    calculation_version: str = "v1.0.0",
) -> UUID:
    """
    Run profitability for all active contracts in a company.
    Creates a ProfitabilityRun with lines for each contract.
    Returns the run's UUID.
    """
    from app.models.core import Contract

    contracts_result = await session.execute(
        select(Contract).where(
            Contract.status == "active",
        )
    )
    contracts = contracts_result.scalars().all()
    # Filter by company via customer
    from app.models.core import Customer

    customer_ids_result = await session.execute(
        select(Customer.id).where(Customer.company_id == company_id)
    )
    company_customer_ids = {row[0] for row in customer_ids_result}
    company_contracts = [c for c in contracts if c.customer_id in company_customer_ids]

    # Create run
    run = ProfitabilityRun(
        id=uuid.uuid4(),
        company_id=company_id,
        run_date=date.today(),
        period_start=period_start,
        period_end=period_end,
        calculation_version=calculation_version,
        status="draft",
    )
    session.add(run)
    await session.flush()

    total_revenue = Decimal("0")
    total_direct_labor = Decimal("0")
    total_burden = Decimal("0")
    total_subcontractor = Decimal("0")

    for contract in company_contracts:
        line = await compute_contract_profitability(
            session=session,
            contract_id=contract.id,
            period_start=period_start,
            period_end=period_end,
            calculation_version=calculation_version,
            run_id=run.id,
            company_id=company_id,
        )
        line.customer_id = contract.customer_id
        session.add(line)

        total_revenue += line.revenue or Decimal("0")
        total_direct_labor += line.direct_labor_cost or Decimal("0")
        total_burden += line.burden_cost or Decimal("0")
        total_subcontractor += line.subcontractor_cost or Decimal("0")

    gross_profit = to_money(total_revenue - total_direct_labor - total_burden - total_subcontractor)
    gross_margin_pct = (
        to_money(gross_profit / total_revenue * 100) if total_revenue > 0 else Decimal("0")
    )

    run.total_revenue = to_money(total_revenue)
    run.direct_labor = to_money(total_direct_labor)
    run.burden_cost = to_money(total_burden)
    run.subcontractor_cost = to_money(total_subcontractor)
    run.gross_profit = gross_profit
    run.gross_margin_pct = gross_margin_pct

    await session.flush()
    return run.id
