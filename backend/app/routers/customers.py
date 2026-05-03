from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.core import Company, Contract, Customer
from app.models.transactions import Invoice
from app.schemas.common import PaginatedResponse
from app.schemas.financial import ConcentrationResponse
from app.utils.money import to_money

router = APIRouter()


@router.get("/")
async def list_customers(
    company_id: UUID | None = Query(None),
    is_active: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
) -> dict:
    q = select(Customer)
    if company_id:
        q = q.where(Customer.company_id == company_id)
    if is_active is not None:
        q = q.where(Customer.is_active == is_active)

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar() or 0

    q = q.order_by(Customer.name).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    customers = result.scalars().all()

    return {
        "items": [
            {
                "id": str(c.id),
                "company_id": str(c.company_id),
                "name": c.name,
                "name_aliases": c.name_aliases,
                "customer_type": c.customer_type,
                "industry": c.industry,
                "is_active": c.is_active,
                "concentration_pct": str(c.concentration_pct) if c.concentration_pct else None,
                "qb_customer_id": c.qb_customer_id,
                "created_at": c.created_at.isoformat(),
            }
            for c in customers
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
    }


@router.get("/{customer_id}")
async def get_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
) -> dict:
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    return {
        "id": str(customer.id),
        "company_id": str(customer.company_id),
        "name": customer.name,
        "name_aliases": customer.name_aliases,
        "customer_type": customer.customer_type,
        "industry": customer.industry,
        "qb_customer_id": customer.qb_customer_id,
        "is_active": customer.is_active,
        "concentration_pct": str(customer.concentration_pct)
        if customer.concentration_pct
        else None,
        "created_at": customer.created_at.isoformat(),
        "updated_at": customer.updated_at.isoformat(),
    }


@router.get("/{customer_id}/contracts")
async def get_customer_contracts(
    customer_id: UUID,
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
) -> dict:
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    q = select(Contract).where(Contract.customer_id == customer_id)
    if status:
        q = q.where(Contract.status == status)
    contracts_result = await db.execute(q.order_by(Contract.start_date.desc()))
    contracts = contracts_result.scalars().all()

    return {
        "customer_id": str(customer_id),
        "contracts": [
            {
                "id": str(c.id),
                "contract_number": c.contract_number,
                "status": c.status,
                "start_date": c.start_date.isoformat(),
                "end_date": c.end_date.isoformat() if c.end_date else None,
                "monthly_value": str(c.monthly_value),
                "contract_type": c.contract_type,
                "scope_creep_flag": c.scope_creep_flag,
            }
            for c in contracts
        ],
    }


@router.get("/{customer_id}/invoices")
async def get_customer_invoices(
    customer_id: UUID,
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
) -> dict:
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    q = select(Invoice).where(Invoice.customer_id == customer_id)
    if status:
        q = q.where(Invoice.status == status)

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar() or 0

    q = q.order_by(Invoice.invoice_date.desc()).offset((page - 1) * page_size).limit(page_size)
    inv_result = await db.execute(q)
    invoices = inv_result.scalars().all()

    return {
        "customer_id": str(customer_id),
        "items": [
            {
                "id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "invoice_date": inv.invoice_date.isoformat(),
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "amount": str(inv.amount),
                "amount_paid": str(inv.amount_paid),
                "status": inv.status,
                "days_outstanding": inv.days_outstanding,
            }
            for inv in invoices
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
    }


@router.get("/{customer_id}/concentration-risk", response_model=list[ConcentrationResponse])
async def get_concentration_risk(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
) -> list[ConcentrationResponse]:
    """
    Returns concentration analysis for all customers in the same company
    as the specified customer.
    """
    cust_result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = cust_result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Get all customers for this company
    all_customers_result = await db.execute(
        select(Customer).where(
            Customer.company_id == customer.company_id, Customer.is_active.is_(True)
        )
    )
    all_customers = all_customers_result.scalars().all()

    # Compute revenue totals per customer from active contracts
    concentrations = []
    company_total = Decimal("0")
    customer_revenues: dict[UUID, Decimal] = {}

    for cust in all_customers:
        contracts_result = await db.execute(
            select(Contract).where(
                Contract.customer_id == cust.id, Contract.status == "active"
            )
        )
        contracts = contracts_result.scalars().all()
        monthly_rev = sum((c.monthly_value for c in contracts), Decimal("0"))
        annual_rev = to_money(monthly_rev * 12)
        customer_revenues[cust.id] = annual_rev
        company_total += annual_rev

    for cust in all_customers:
        rev = customer_revenues.get(cust.id, Decimal("0"))
        pct = (rev / company_total * 100) if company_total > 0 else Decimal("0")
        concentrations.append(
            ConcentrationResponse(
                customer_id=cust.id,
                customer_name=cust.name,
                revenue_total=rev,
                concentration_pct=to_money(pct),
                is_flagged=pct >= 20,
                contract_count=sum(
                    1
                    for _ in await (
                        await db.execute(
                            select(func.count(Contract.id)).where(
                                Contract.customer_id == cust.id, Contract.status == "active"
                            )
                        )
                    )
                    .scalars()
                    .all()
                    if True
                ),
            )
        )

    # Simpler re-implementation for contract counts
    final = []
    for cust in all_customers:
        rev = customer_revenues.get(cust.id, Decimal("0"))
        pct = (rev / company_total * 100) if company_total > 0 else Decimal("0")
        count_result = await db.execute(
            select(func.count(Contract.id)).where(
                Contract.customer_id == cust.id, Contract.status == "active"
            )
        )
        count = count_result.scalar() or 0
        final.append(
            ConcentrationResponse(
                customer_id=cust.id,
                customer_name=cust.name,
                revenue_total=rev,
                concentration_pct=to_money(pct),
                is_flagged=pct >= 20,
                contract_count=count,
            )
        )

    return sorted(final, key=lambda x: x.concentration_pct, reverse=True)
