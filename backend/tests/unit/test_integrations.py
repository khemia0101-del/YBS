"""Integration connector framework tests (no external API calls)."""
from __future__ import annotations

import pytest

from app.services.integrations import IntegrationError, get_connector
from app.services.integrations.gmail_connector import GmailConnector
from app.services.integrations.plaid_connector import PlaidConnector
from app.services.integrations.quickbooks_connector import QuickBooksConnector


def test_get_connector_resolves_known_providers():
    import uuid

    cid = uuid.uuid4()
    assert isinstance(get_connector("plaid", cid), PlaidConnector)
    assert isinstance(get_connector("quickbooks", cid), QuickBooksConnector)
    assert isinstance(get_connector("gmail", cid), GmailConnector)


def test_get_connector_rejects_unknown_provider():
    import uuid

    with pytest.raises(IntegrationError):
        get_connector("bogus", uuid.uuid4())


@pytest.mark.asyncio
async def test_token_store_load_roundtrip(db_session, sample_company):
    connector = PlaidConnector(sample_company.id)
    assert await connector.is_connected(db_session) is False

    await connector.store_tokens(
        db_session, {"access_token": "tok-abc", "cursor": None}, metadata={"item_id": "i1"}
    )
    loaded = await connector.load_tokens(db_session)
    assert loaded == {"access_token": "tok-abc", "cursor": None}
    assert await connector.is_connected(db_session) is True


@pytest.mark.asyncio
async def test_store_tokens_deactivates_prior_credential(db_session, sample_company):
    connector = QuickBooksConnector(sample_company.id)
    await connector.store_tokens(db_session, {"access_token": "old"})
    await connector.store_tokens(db_session, {"access_token": "new"})

    # Only the latest credential is active and returned.
    loaded = await connector.load_tokens(db_session)
    assert loaded == {"access_token": "new"}


@pytest.mark.asyncio
async def test_persist_creates_company_scoped_records_and_dedups(
    db_session, sample_company
):
    from sqlalchemy import func, select

    from app.models.raw import RawRecord

    connector = PlaidConnector(sample_company.id)
    items = [{"id": "t1", "amount": 10}, {"id": "t2", "amount": 20}]

    first = await connector._persist(db_session, items)
    assert first == 2

    # Re-persisting the same items is a no-op (checksum dedup).
    second = await connector._persist(db_session, items)
    assert second == 0

    total = await db_session.execute(
        select(func.count(RawRecord.id)).where(
            RawRecord.company_id == sample_company.id
        )
    )
    assert total.scalar() == 2


@pytest.mark.asyncio
async def test_disconnect_removes_active_credential(db_session, sample_company):
    connector = GmailConnector(sample_company.id)
    await connector.store_tokens(db_session, {"access_token": "g"})
    assert await connector.disconnect(db_session) is True
    assert await connector.is_connected(db_session) is False
