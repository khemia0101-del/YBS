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
from app.models.core import Company, Contract, Customer, Site, Tenant
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

        # ── Tenants ────────────────────────────────────────────────────────
        # Tenant 1 — the operator's account (runs CRR + other businesses).
        # Tenant 2 — a separate, isolated tenant proving data isolation.
        tenant1 = Tenant(
            id=uuid.uuid4(), name="YBS Holdings", slug="ybs", is_active=True
        )
        tenant2 = Tenant(
            id=uuid.uuid4(), name="Acme Co", slug="acme-co", is_active=True
        )
        session.add_all([tenant1, tenant2])
        print(f"  Created tenants: {tenant1.name}, {tenant2.name}")

        # ── Users ──────────────────────────────────────────────────────────
        admin = User(
            id=uuid.uuid4(),
            tenant_id=tenant1.id,
            email="admin@ybs-os.dev",
            hashed_password=hash_password("admin1234!"),
            full_name="Admin User",
            role="admin",
            is_active=True,
        )
        analyst = User(
            id=uuid.uuid4(),
            tenant_id=tenant1.id,
            email="analyst@ybs-os.dev",
            hashed_password=hash_password("analyst1234!"),
            full_name="Sarah Analyst",
            role="analyst",
            is_active=True,
        )
        tenant2_admin = User(
            id=uuid.uuid4(),
            tenant_id=tenant2.id,
            email="admin@acme-co.dev",
            hashed_password=hash_password("admin1234!"),
            full_name="Acme Admin",
            role="admin",
            is_active=True,
        )
        session.add_all([admin, analyst, tenant2_admin])
        print(
            f"  Created users: {admin.email}, {analyst.email}, {tenant2_admin.email}"
        )

        # ── Companies ──────────────────────────────────────────────────────
        company = Company(
            id=uuid.uuid4(),
            tenant_id=tenant1.id,
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
        # Credit Repair Resources LLC — the acquisition target.
        crr = Company(
            id=uuid.uuid4(),
            tenant_id=tenant1.id,
            legal_name="Credit Repair Resources LLC",
            dba_name="Credit Repair Resources",
            ein="34-1987654",
            address={"city": "Cleveland", "state": "OH"},
            founded_date=date(2007, 1, 1),
            acquisition_target=True,
        )
        # A company belonging to the second, isolated tenant.
        acme = Company(
            id=uuid.uuid4(),
            tenant_id=tenant2.id,
            legal_name="Acme Holdings LLC",
            dba_name="Acme",
            founded_date=date(2019, 3, 1),
            acquisition_target=False,
        )
        session.add_all([company, crr, acme])
        print(
            f"  Created companies: {company.legal_name}, {crr.legal_name}, "
            f"{acme.legal_name}"
        )

        # ── CRR adaptive business profile + KPI definitions ────────────────
        from app.models.business import BusinessProfile
        from app.services.business.profile import (
            CREDIT_REPAIR_METRICS,
            build_metric_definitions,
        )

        crr_profile = BusinessProfile(
            id=uuid.uuid4(),
            company_id=crr.id,
            industry="Credit Repair Services",
            business_model="subscription",
            description=(
                "Credit repair agency: $399 enrollment + $165/mo for 7 months, "
                "then $9.99/mo maintenance. Proprietary dispute-management software."
            ),
            north_star_metric="active_members",
            growth_goal={
                "metric_key": "active_members",
                "current_value": 200,  # placeholder — refined by QoE/metrics ingestion
                "target_value": 1000,
                "deadline": "2026-12-31",
            },
            source="manual",
            is_confirmed=True,
        )
        session.add(crr_profile)
        await session.flush()
        crr_metrics = build_metric_definitions(
            crr.id, crr_profile.id, CREDIT_REPAIR_METRICS
        )
        session.add_all(crr_metrics)
        print(
            f"  Created CRR business profile + {len(crr_metrics)} metric definitions"
        )

        # ── CRR metric snapshots (Jan-May 2025 trend) ──────────────────────
        from app.models.business import MetricSnapshot

        by_key = {m.key: m for m in crr_metrics}
        snapshot_data = {
            "active_members": [180, 185, 190, 196, 205],
            "mrr": [21000, 21500, 22000, 22500, 23000],
            "new_enrollments": [5, 6, 5, 6, 6],
            "files_per_month": [10, 12, 11, 13, 12],
            "gross_margin": [97.4, 97.3, 97.5, 97.4, 97.4],
        }
        months_2025 = [date(2025, m, 1) for m in range(1, 6)]
        snap_count = 0
        for key, values in snapshot_data.items():
            metric = by_key.get(key)
            if metric is None:
                continue
            for period_dt, v in zip(months_2025, values):
                session.add(
                    MetricSnapshot(
                        id=uuid.uuid4(),
                        company_id=crr.id,
                        metric_definition_id=metric.id,
                        period_date=period_dt,
                        period_type="monthly",
                        value=Decimal(str(v)),
                        source="manual",
                    )
                )
                snap_count += 1
        print(f"  Created {snap_count} CRR metric snapshots")

        # ── CRR QoE run (seeded baseline) ──────────────────────────────────
        from app.models.esop import QoERun
        from app.services.qoe.crr_data import CRR_PERIODS, VALUATION_RATIONALE
        from app.services.qoe.engine import analyze as qoe_analyze
        from app.services.qoe.valuation import value_by_sde

        crr_qoe = qoe_analyze(CRR_PERIODS, primary_label="FY2024")
        crr_val = value_by_sde(
            crr_qoe.primary.sde, 2.0, 2.75, 3.5, rationale=VALUATION_RATIONALE
        )
        session.add(
            QoERun(
                id=uuid.uuid4(),
                company_id=crr.id,
                run_date=date.today(),
                analysis_period_start=date(2024, 1, 1),
                analysis_period_end=date(2024, 12, 31),
                status="draft",
                reported_ebitda=crr_qoe.primary.reported_ebitda,
                adjusted_ebitda=crr_qoe.primary.adjusted_ebitda,
                normalized_ebitda=crr_qoe.primary.sde,
                evidence_bundle={
                    "qoe": crr_qoe.as_dict(),
                    "valuation": crr_val.as_dict(),
                },
            )
        )
        print("  Created CRR QoE run (FY2024 baseline)")

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

        # ── CRR continuous ops loops ───────────────────────────────────────
        from app.models.ops_loop import OpsLoop

        session.add_all(
            [
                OpsLoop(
                    id=uuid.uuid4(),
                    company_id=crr.id,
                    name="Weekly metrics & funnel review",
                    focus="metrics",
                    prompt=(
                        "Review week-over-week movement in active_members, MRR, "
                        "new_enrollments, and dispute success rate. Highlight "
                        "outliers and propose specific, named follow-ups."
                    ),
                    schedule_cron="0 9 * * 1",
                    is_active=True,
                ),
                OpsLoop(
                    id=uuid.uuid4(),
                    company_id=crr.id,
                    name="Daily cash health watch",
                    focus="cash",
                    prompt=(
                        "Check cash balance, AR aging, and upcoming committed "
                        "expenses. Propose action ONLY if cash runway falls "
                        "below 60 days or AR > 45 days drifts upward."
                    ),
                    schedule_cron="0 7 * * *",
                    is_active=True,
                ),
            ]
        )
        print("  Created 2 CRR continuous ops loops")

        await session.commit()
        print("\nSeed complete!")
        print(f"   Tenant 1 ({tenant1.name}):")
        print(f"     Admin login:   admin@ybs-os.dev / admin1234!")
        print(f"     Analyst login: analyst@ybs-os.dev / analyst1234!")
        print(f"     Company (YBS): {company.id}")
        print(f"     Company (CRR): {crr.id}")
        print(f"   Tenant 2 ({tenant2.name}):")
        print(f"     Admin login:   admin@acme-co.dev / admin1234!")
        print(f"     Company (Acme): {acme.id}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
