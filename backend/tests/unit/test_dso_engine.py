"""
Unit tests for the DSO calculation engine.
Uses SQLite in-memory (via session fixture from conftest).
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Customer
from app.models.transactions import Invoice
from app.services.financial.dso_engine import compute_dso
from app.utils.money import to_money


async def _add_invoice(
    session: AsyncSession,
    company_id: uuid.UUID,
    customer_id: uuid.UUID,
    amount: Decimal,
    invoice_date: date,
    amount_paid: Decimal = Decimal("0"),
    status: str = "open",
) -> Invoice:
    inv = Invoice(
        id=uuid.uuid4(),
        company_id=company_id,
        customer_id=customer_id,
        invoice_date=invoice_date,
        amount=amount,
        amount_paid=amount_paid,
        status=status,
    )
    session.add(inv)
    await session.flush()
    return inv


@pytest.mark.asyncio
async def test_dso_zero_when_no_invoices(
    db_session: AsyncSession, sample_company
) -> None:
    """With no invoices, DSO should be 0."""
    snap = await compute_dso(db_session, sample_company.id, date.today())
    assert snap.dso_days == Decimal("0")
    assert snap.total_ar == Decimal("0")
    assert snap.avg_daily_revenue == Decimal("0")


@pytest.mark.asyncio
async def test_dso_basic_calculation(
    db_session: AsyncSession, sample_company, sample_customer
) -> None:
    """
    DSO = (AR / revenue_90_days) * 90

    Setup:
    - Revenue in last 90 days: $9000 (3 invoices of $3000 each)
    - Open AR: $6000 (2 invoices unpaid)
    - Expected DSO = (6000 / 9000) * 90 = 60 days
    """
    today = date.today()
    cid = sample_company.id
    cust_id = sample_customer.id

    # Revenue invoices (all in trailing 90 days)
    await _add_invoice(db_session, cid, cust_id, Decimal("3000"), today - timedelta(days=10), amount_paid=Decimal("3000"), status="paid")
    await _add_invoice(db_session, cid, cust_id, Decimal("3000"), today - timedelta(days=30), status="open")
    await _add_invoice(db_session, cid, cust_id, Decimal("3000"), today - timedelta(days=60), status="open")

    snap = await compute_dso(db_session, cid, today)

    assert snap.total_ar == Decimal("6000.00")
    # avg_daily_revenue = 9000 / 90 = 100.00
    assert snap.avg_daily_revenue == Decimal("100.00")
    # dso = 6000 / 100 = 60
    assert snap.dso_days == Decimal("60.00")


@pytest.mark.asyncio
async def test_dso_aging_buckets(
    db_session: AsyncSession, sample_company, sample_customer
) -> None:
    """Aging buckets are correctly assigned by invoice_date age."""
    today = date.today()
    cid = sample_company.id
    cust_id = sample_customer.id

    await _add_invoice(db_session, cid, cust_id, Decimal("1000"), today - timedelta(days=15), status="open")   # 0-30
    await _add_invoice(db_session, cid, cust_id, Decimal("2000"), today - timedelta(days=45), status="open")   # 31-60
    await _add_invoice(db_session, cid, cust_id, Decimal("3000"), today - timedelta(days=75), status="open")   # 61-90
    await _add_invoice(db_session, cid, cust_id, Decimal("4000"), today - timedelta(days=120), status="overdue")  # 91+

    snap = await compute_dso(db_session, cid, today)

    assert snap.aging_0_30 == Decimal("1000.00")
    assert snap.aging_31_60 == Decimal("2000.00")
    assert snap.aging_61_90 == Decimal("3000.00")
    assert snap.aging_91_plus == Decimal("4000.00")
    assert snap.total_ar == Decimal("10000.00")


@pytest.mark.asyncio
async def test_dso_excludes_voided_invoices(
    db_session: AsyncSession, sample_company, sample_customer
) -> None:
    """Voided invoices should not appear in AR or revenue."""
    today = date.today()
    cid = sample_company.id
    cust_id = sample_customer.id

    await _add_invoice(db_session, cid, cust_id, Decimal("5000"), today - timedelta(days=10), status="open")
    await _add_invoice(db_session, cid, cust_id, Decimal("99999"), today - timedelta(days=5), status="void")

    snap = await compute_dso(db_session, cid, today)
    assert snap.total_ar == Decimal("5000.00")


@pytest.mark.asyncio
async def test_dso_snapshot_persisted(
    db_session: AsyncSession, sample_company, sample_customer
) -> None:
    """compute_dso should flush a DSOSnapshot to the session."""
    today = date.today()
    await _add_invoice(
        db_session, sample_company.id, sample_customer.id,
        Decimal("1000"), today - timedelta(days=5), status="open"
    )
    snap = await compute_dso(db_session, sample_company.id, today)
    assert snap.id is not None
    assert snap.company_id == sample_company.id
    assert snap.snapshot_date == today
