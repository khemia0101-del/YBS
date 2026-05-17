"""Gmail connector — read-only OAuth2 access for operational signals."""
from __future__ import annotations

from datetime import datetime
from urllib.parse import urlencode

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.integrations.base import BaseConnector, IntegrationError

_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


class GmailConnector(BaseConnector):
    provider = "gmail"

    @staticmethod
    def authorize_url(state: str) -> str:
        if not settings.GOOGLE_CLIENT_ID:
            raise IntegrationError("Gmail is not configured — set GOOGLE_CLIENT_ID.")
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": _SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, db: AsyncSession, code: str) -> dict:
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise IntegrationError("Gmail is not configured.")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                _TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
        if resp.status_code != 200:
            raise IntegrationError(f"Gmail token exchange failed: {resp.text[:300]}")
        await self.store_tokens(db, resp.json())
        return {"connected": True}

    async def fetch(self, db: AsyncSession, since: datetime | None) -> list[dict]:
        tokens = await self.load_tokens(db)
        if not tokens:
            raise IntegrationError("Gmail is not connected for this business.")
        access_token = tokens.get("access_token", "")
        headers = {"Authorization": f"Bearer {access_token}"}

        query = ""
        if since:
            query = f"after:{int(since.timestamp())}"

        async with httpx.AsyncClient(timeout=30) as client:
            listing = await client.get(
                f"{_GMAIL_API}/messages",
                params={"maxResults": 100, "q": query},
                headers=headers,
            )
            if listing.status_code != 200:
                raise IntegrationError(
                    f"Gmail list failed {listing.status_code}: {listing.text[:300]}"
                )
            message_ids = [m["id"] for m in listing.json().get("messages", [])]

            messages: list[dict] = []
            for mid in message_ids:
                detail = await client.get(
                    f"{_GMAIL_API}/messages/{mid}",
                    params={"format": "metadata",
                            "metadataHeaders": ["From", "To", "Subject", "Date"]},
                    headers=headers,
                )
                if detail.status_code == 200:
                    messages.append(detail.json())
        return messages
