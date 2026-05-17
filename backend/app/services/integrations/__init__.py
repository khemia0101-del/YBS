"""Integration connectors — direct API clients for headless data syncing."""
from __future__ import annotations

from uuid import UUID

from app.services.integrations.base import BaseConnector, IntegrationError
from app.services.integrations.gmail_connector import GmailConnector
from app.services.integrations.plaid_connector import PlaidConnector
from app.services.integrations.quickbooks_connector import QuickBooksConnector

CONNECTORS: dict[str, type[BaseConnector]] = {
    "plaid": PlaidConnector,
    "quickbooks": QuickBooksConnector,
    "gmail": GmailConnector,
}


def get_connector(provider: str, company_id: UUID) -> BaseConnector:
    cls = CONNECTORS.get(provider)
    if cls is None:
        raise IntegrationError(
            f"Unknown integration provider '{provider}'. "
            f"Supported: {sorted(CONNECTORS)}"
        )
    return cls(company_id)


__all__ = ["CONNECTORS", "get_connector", "BaseConnector", "IntegrationError"]
