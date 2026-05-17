from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from app.models.base import Base
from app.models.core import Company, Contract, Customer, Tenant
from app.models.users import User
from app.security.auth import hash_password

# Use SQLite in-memory for tests (no Postgres required)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@compiles(ARRAY, "sqlite")
def _render_array_as_text_on_sqlite(element, compiler, **kw):
    """SQLite has no ARRAY type — render it as TEXT so create_all() works."""
    return "TEXT"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create a test database engine."""
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncSession:
    """
    Provide a transactional AsyncSession that rolls back after each test.
    This keeps tests isolated without needing to truncate tables.
    """
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def sample_tenant(db_session: AsyncSession) -> Tenant:
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Sample Tenant",
        slug=f"sample-{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest_asyncio.fixture
async def sample_company(db_session: AsyncSession, sample_tenant: Tenant) -> Company:
    company = Company(
        id=uuid.uuid4(),
        tenant_id=sample_tenant.id,
        legal_name="YBS Cleaning Solutions LLC",
        dba_name="YBS Clean",
        ein="12-3456789",
        address={"street": "123 Main St", "city": "Houston", "state": "TX", "zip": "77001"},
        founded_date=date(2015, 3, 1),
        acquisition_target=True,
    )
    db_session.add(company)
    await db_session.flush()
    return company


@pytest_asyncio.fixture
async def sample_customer(db_session: AsyncSession, sample_company: Company) -> Customer:
    customer = Customer(
        id=uuid.uuid4(),
        company_id=sample_company.id,
        name="Acme Corporation",
        name_aliases=["Acme Corp", "ACME"],
        customer_type="commercial",
        industry="manufacturing",
        is_active=True,
        concentration_pct=Decimal("0.3500"),
    )
    db_session.add(customer)
    await db_session.flush()
    return customer


@pytest_asyncio.fixture
async def sample_contract(
    db_session: AsyncSession, sample_customer: Customer
) -> Contract:
    contract = Contract(
        id=uuid.uuid4(),
        customer_id=sample_customer.id,
        contract_number="CTR-001",
        start_date=date(2024, 1, 1),
        monthly_value=Decimal("12500.00"),
        contract_type="fixed",
        status="active",
        auto_renews=True,
        renewal_notice_days=30,
    )
    db_session.add(contract)
    await db_session.flush()
    return contract


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="admin@ybs-os.internal",
        hashed_password=hash_password("adminpassword123"),
        full_name="Admin User",
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def analyst_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="analyst@ybs-os.internal",
        hashed_password=hash_password("analystpassword123"),
        full_name="Analyst User",
        role="analyst",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user
