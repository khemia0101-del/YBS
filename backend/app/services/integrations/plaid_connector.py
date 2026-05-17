"""Plaid connector — bank account access via Plaid Link + /transactions/sync."""
from __future__ import annotations

from datetime import datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.integrations.base import BaseConnector, IntegrationError

_PLAID_HOSTS = {
    "sandbox": "https://sandbox.plaid.com",
    "development": "https://development.plaid.com",
    "production": "https://production.plaid.com",
}


class PlaidConnector(BaseConnector):
    provider = "plaid"

    @staticmethod
    def _host() -> str:
        return _PLAID_HOSTS.get(settings.PLAID_ENV, _PLAID_HOSTS["sandbox"])

    @staticmethod
    def _auth() -> dict:
        if not settings.PLAID_CLIENT_ID or not settings.PLAID_SECRET:
            raise IntegrationError(
                "Plaid is not configured — set PLAID_CLIENT_ID and PLAID_SECRET."
            )
        return {
            "client_id": settings.PLAID_CLIENT_ID,
            "secret": settings.PLAID_SECRET,
        }

    async def _post(self, path: str, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{self._host()}{path}", json=payload)
        if resp.status_code != 200:
            raise IntegrationError(f"Plaid {path} failed {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    async def create_link_token(self) -> str:
        """Create a Link token the frontend Plaid Link widget uses to start the flow."""
        data = await self._post(
            "/link/token/create",
            {
                **self._auth(),
                "user": {"client_user_id": str(self.company_id)},
                "client_name": "YBS OS",
                "products": ["transactions"],
                "country_codes": ["US"],
                "language": "en",
            },
        )
        return data["link_token"]

    async def exchange_public_token(self, db: AsyncSession, public_token: str) -> dict:
        """Exchange the public token from Plaid Link for a long-lived access token."""
        data = await self._post(
            "/item/public_token/exchange",
            {**self._auth(), "public_token": public_token},
        )
        await self.store_tokens(
            db,
            {"access_token": data["access_token"], "cursor": None},
            metadata={"item_id": data.get("item_id")},
        )
        return {"item_id": data.get("item_id")}

    async def fetch(self, db: AsyncSession, since: datetime | None) -> list[dict]:
        tokens = await self.load_tokens(db)
        if not tokens:
            raise IntegrationError("Plaid is not connected for this business.")
        access_token = tokens["access_token"]
        cursor = tokens.get("cursor")

        added: list[dict] = []
        has_more = True
        while has_more:
            payload = {**self._auth(), "access_token": access_token}
            if cursor:
                payload["cursor"] = cursor
            data = await self._post("/transactions/sync", payload)
            added.extend(data.get("added", []))
            cursor = data.get("next_cursor")
            has_more = data.get("has_more", False)

        # Persist the cursor so the next sync only pulls new transactions.
        await self.store_tokens(
            db,
            {"access_token": access_token, "cursor": cursor},
            metadata={"item_id": (tokens.get("item_id"))},
        )
        return added
