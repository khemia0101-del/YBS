"""QuickBooks Online connector — OAuth2 + invoice/transaction sync."""
from __future__ import annotations

from datetime import datetime
from urllib.parse import urlencode

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.integrations.base import BaseConnector, IntegrationError

_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
_AUTH_URL = "https://appcenter.intuit.com/connect/oauth2"


class QuickBooksConnector(BaseConnector):
    provider = "quickbooks"

    @staticmethod
    def _api_host() -> str:
        return (
            "https://quickbooks.api.intuit.com"
            if settings.QB_ENVIRONMENT == "production"
            else "https://sandbox-quickbooks.api.intuit.com"
        )

    @staticmethod
    def authorize_url(state: str) -> str:
        if not settings.QB_CLIENT_ID:
            raise IntegrationError("QuickBooks is not configured — set QB_CLIENT_ID.")
        params = {
            "client_id": settings.QB_CLIENT_ID,
            "response_type": "code",
            "scope": "com.intuit.quickbooks.accounting",
            "redirect_uri": settings.QB_REDIRECT_URI,
            "state": state,
        }
        return f"{_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(
        self, db: AsyncSession, code: str, realm_id: str
    ) -> dict:
        if not settings.QB_CLIENT_ID or not settings.QB_CLIENT_SECRET:
            raise IntegrationError("QuickBooks is not configured.")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                _TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.QB_REDIRECT_URI,
                },
                auth=(settings.QB_CLIENT_ID, settings.QB_CLIENT_SECRET),
            )
        if resp.status_code != 200:
            raise IntegrationError(f"QB token exchange failed: {resp.text[:300]}")
        tokens = resp.json()
        await self.store_tokens(db, tokens, metadata={"realm_id": realm_id})
        return {"realm_id": realm_id}

    async def fetch(self, db: AsyncSession, since: datetime | None) -> list[dict]:
        cred_tokens = await self.load_tokens(db)
        cred = await self._active_credential(db)
        if not cred_tokens or cred is None:
            raise IntegrationError("QuickBooks is not connected for this business.")
        realm_id = (cred.metadata_json or {}).get("realm_id")
        if not realm_id:
            raise IntegrationError("QuickBooks credential is missing a realm_id.")

        access_token = cred_tokens.get("access_token", "")
        query = "SELECT * FROM Invoice MAXRESULTS 1000"
        if since:
            iso = since.isoformat()
            query = (
                f"SELECT * FROM Invoice WHERE MetaData.LastUpdatedTime >= '{iso}' "
                "MAXRESULTS 1000"
            )
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self._api_host()}/v3/company/{realm_id}/query",
                params={"query": query, "minorversion": "65"},
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
        if resp.status_code != 200:
            raise IntegrationError(f"QB API error {resp.status_code}: {resp.text[:300]}")
        return resp.json().get("QueryResponse", {}).get("Invoice", [])
