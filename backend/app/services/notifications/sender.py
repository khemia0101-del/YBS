"""Outbound notifications — employee email via SendGrid."""
from __future__ import annotations

import httpx

from app.config import settings


async def send_email(to_email: str, subject: str, body: str) -> dict:
    """
    Send a plain-text email via SendGrid.

    Returns ``{"status", "detail"}``. If SendGrid is not configured the call is
    a no-op with status ``"skipped"`` — never raises, so it cannot break the
    approval flow.
    """
    if not settings.SENDGRID_API_KEY:
        return {"status": "skipped", "detail": "SENDGRID_API_KEY is not configured"}

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": settings.NOTIFICATIONS_FROM_EMAIL},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body}],
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={"Authorization": f"Bearer {settings.SENDGRID_API_KEY}"},
                json=payload,
            )
    except httpx.HTTPError as exc:
        return {"status": "failed", "detail": f"network error: {exc}"}

    if resp.status_code in (200, 202):
        return {"status": "sent", "detail": f"HTTP {resp.status_code}"}
    return {"status": "failed", "detail": f"HTTP {resp.status_code}: {resp.text[:200]}"}
