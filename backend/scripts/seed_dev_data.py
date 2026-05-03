#!/usr/bin/env python3
"""
Seed development database with realistic YBS OS data.

Creates:
- 1 company
- 3 customers (commercial, government, nonprofit)
- 5 contracts (various types and statuses)
- 20 invoices with realistic amounts and aging
- Labor burden assumptions
- 1 admin user, 1 analyst user

Usage:
    cd /home/user/YBS/backend
    python scripts/seed_dev_data.py
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import date, timedelta
from decimal import Decimal
from random import choice, randint, uniform

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Must set DATABASE_URL in env or .env before running
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.models.base import Base
from app.models.core import Company, Contract, Customer, Site
from app.models.financial import LaborBurdenAssumption
from app.models.transactions import Invoice, Payment
from app.models.users import User
from app.security.auth import hash_password
from app.utils.money import to_money


async def seed() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        print("Seeding development data...")

        # ── Users ──────────────────────────────────────────────────────────
        admin = User(
            id=uuid.uuid4(),
            email="admin@ybs-os.dev",
            hashed_password=hash_password("admin1234!"),
            full_name="Admin User",
            role="admin",
            is_active=True,
        )
        analyst = User(
            id=uuid.uuid4(),
            email="analyst@ybs-os.dev",
            hashed_password=hash_password("analyst1234!"),
            full_name="Sarah Analyst",
            role="analyst",
            is_active=True,
        )
        session.add_all([admin, analyst])
        print(f"  Created users: {admin.email}, {analyst.email}")

        # ── Company ────────────────────────────────────────────────────────
        company = Company(
            id=uuid.uuid4(),
            legal_name="YBS Building Services LLC",
            dba_name="YBS Clean",
            ein="83-1234567",
            address={
                "street": "1500 Allen Pkwy",
                "city": "Houston",
                "state": "TX",
                "zip": "77019",
            },
            founded_date=date(2016, 6, 15),
            acquisition_target=True,
        )
        session.add(company)
        print(f"  Created company: {company.legal_name}")

        # ── Labor Burden Assumptions ───────────────────────────────────────
        burden = LaborBurdenAssumption(
            id=uuid.uuid4(),
            company_id=company.id,
            version="v1.0.0",
            fica_employer_pct=Decimal("0.0765"),
            futa_pct=Decimal("0.006"),
            suta_pct=Decimal("0.027"),
            workers_comp_pct=Decimal("0.042"),
            benefits_pct=Decimal("0.08"),
            training_pct=Decimal("0.005"),
            total_burden_pct=Decimal("0.2365"),
            is_active=True,
            effective_date=date(2024, 1, 1),
        )
        session.add(burden)

        # ── Customers ──────────────────────────────────────────────────────
        customers_data = [
            {
                "name": "Acme Manufacturing Corp",
                "aliases": ["Acme Mfg", "ACME"],
                "type": "commercial",
                "industry": "manufacturing",
                "qb_id": "QB-CUST-001",
                "concentration": Decimal("0.4200"),
            },
            {
                "name": "City of Houston Public Works",
                "aliases": ["Houston Public Works", "City of Houston"],
                "type": "government",
                "industry": "government",
                "qb_id": "QB-CUST-002",
                "concentration": Decimal("0.3500"),
            },
            {
                "name": "Bay Area Community Foundation",
                "aliases": ["BACF", "Bay Area Foundation"],
                "type": "nonprofit",
                "industry": "nonprofit",
                "qb_id": "QB-CUST-003",
                "concentration": Decimal("0.2300"),
            },
        ]

        customers = []
        for cd in customers_data:
            cust = Customer(
                id=uuid.uuid4(),
                company_id=company.id,
                name=cd["name"],
                name_aliases=cd["aliases"],
                customer_type=cd["type"],
                industry=cd["industry"],
                qb_customer_id=cd["qb_id"],
                is_active=True,
                concentration_pct=cd["concentration"],
            )
            session.add(cust)
            customers.append(cust)
        print(f"  Created {len(customers)} customers")

        # ── Sites ──────────────────────────────────────────────────────────
        sites = []
        site_addresses = [
            {"street": "500 Westpark Dr", "city": "Houston", "state": "TX", "zip": "77042"},
            {"street": "1200 McKinney St", "city": "Houston", "state": "TX", "zip": "77010"},
            {"street": "4300 Main St", "city": "Houston", "state": "TX", "zip": "77002"},
        ]
        for i, (cust, addr) in enumerate(zip(customers, site_addresses)):
            site = Site(
                id=uuid.uuid4(),
                customer_id=cust.id,
                site_name=f"{cust.name} — Main Site",
                address=addr,
                square_footage=Decimal(str(randint(15000, 80000))),
                swept_site_id=f"SWEPT-{1000 + i}",
                is_active=True,
            )
            session.add(site)
            sites.append(site)

        # ── Contracts ──────────────────────────────────────────────────────
        contracts_config = [
            # Acme — large fixed contract, active
            {
                "customer": customers[0],
                "site": sites[0],
                "number": "CTR-2024-001",
                "start": date(2024, 1, 1),
                "end": date(2025, 12, 31),
                "monthly": Decimal("18500.00"),
                "type": "fixed",
                "status": "active",
                "auto_renews": True,
                "frequency": "5x/week",
            },
            # Acme — variable add-on, active
            {
                "customer": customers[0],
                "site": sites[0],
                "number": "CTR-2024-002",
                "start": date(2024, 3, 1),
                "end": None,
                "monthly": Decimal("4200.00"),
                "type": "variable",
                "status": "active",
                "auto_renews": False,
                "frequency": "on-demand",
            },
            # Houston — government T&M, active
            {
                "customer": customers[1],
                "site": sites[1],
                "number": "CTR-2024-003",
                "start": date(2024, 2, 1),
                "end": date(2025, 1, 31),
                "monthly": Decimal("11000.00"),
                "type": "t_and_m",
                "status": "active",
                "auto_renews": False,
                "frequency": "3x/week",
            },
            # Foundation — small, active
            {
                "customer": customers[2],
                "site": sites[2],
                "number": "CTR-2023-007",
                "start": date(2023, 7, 1),
                "end": date(2024, 6, 30),
                "monthly": Decimal("3800.00"),
                "type": "fixed",
                "status": "active",
                "auto_renews": True,
                "frequency": "2x/week",
            },
            # Expired Acme contract
            {
                "customer": customers[0],
                "site": None,
                "number": "CTR-2022-001",
                "start": date(2022, 1, 1),
                "end": date(2023, 12, 31),
                "monthly": Decimal("9500.00"),
                "type": "fixed",
                "status": "expired",
                "auto_renews": False,
                "frequency": "5x/week",
            },
        ]

        contracts = []
        for cc in contracts_config:
            c = Contract(
                id=uuid.uuid4(),
                customer_id=cc["customer"].id,
                site_id=cc["site"].id if cc["site"] else None,
                contract_number=cc["number"],
                start_date=cc["start"],
                end_date=cc["end"],
                monthly_value=cc["monthly"],
                contract_type=cc["type"],
                status=cc["status"],
                auto_renews=cc["auto_renews"],
                renewal_notice_days=30,
                service_frequency=cc["frequency"],
                scope_creep_flag=False,
                confidence_score=Decimal("0.9500"),
                calculation_version="v1.0.0",
            )
            session.add(c)
            contracts.append(c)
        print(f"  Created {len(contracts)} contracts")

        # ── Invoices (20 total) ────────────────────────────────────────────
        invoice_statuses = ["paid", "paid", "paid", "open", "open", "overdue", "partial"]
        today = date.today()
        invoice_count = 0

        for contract in contracts[:4]:  # Skip expired contract
            cust = next(c for c in customers if c.id == contract.customer_id)
            monthly = contract.monthly_value

            # Generate 4-6 invoices per contract
            num_invoices = randint(4, 6)
            for i in range(num_invoices):
                inv_date = today.replace(day=1) - timedelta(days=30 * i)
                due_date = inv_date + timedelta(days=30)
                status = choice(invoice_statuses)

                # Add some variance to monthly amounts
                variance = Decimal(str(uniform(0.95, 1.05)))
                amount = to_money(monthly * variance)

                amount_paid = Decimal("0")
                if status == "paid":
                    amount_paid = amount
                elif status == "partial":
                    amount_paid = to_money(amount * Decimal("0.5"))

                days_outstanding = (today - inv_date).days

                inv = Invoice(
                    id=uuid.uuid4(),
                    company_id=company.id,
                    customer_id=cust.id,
                    contract_id=contract.id,
                    invoice_number=f"INV-{today.year}-{invoice_count + 1:04d}",
                    invoice_date=inv_date,
                    due_date=due_date,
                    amount=amount,
                    amount_paid=amount_paid,
                    status=status,
                    days_outstanding=days_outstanding,
                    confidence_score=Decimal("0.9500"),
                    calculation_version="v1.0.0",
                )
                session.add(inv)
                invoice_count += 1

                # Add a payment record for paid invoices
                if status == "paid" and amount_paid > 0:
                    payment = Payment(
                        id=uuid.uuid4(),
                        company_id=company.id,
                        customer_id=cust.id,
                        invoice_id=inv.id,
                        payment_date=due_date - timedelta(days=randint(0, 5)),
                        amount=amount_paid,
                        payment_method="ach",
                        reference_number=f"REF-{inv.invoice_number}",
                        match_status="matched",
                        match_confidence=Decimal("0.9800"),
                    )
                    session.add(payment)

        print(f"  Created {invoice_count} invoices with payments")

        await session.commit()
        print("\n✅ Seed complete!")
        print(f"   Admin login:   admin@ybs-os.dev / admin1234!")
        print(f"   Analyst login: analyst@ybs-os.dev / analyst1234!")
        print(f"   Company ID:    {company.id}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
