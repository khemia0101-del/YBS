"""
Shared Anthropic (Claude) client.

Used by the AI interviewer, automation analysis, profit advisor, and the AI COO.
The system prompt is sent with ``cache_control`` so repeated calls that share a
large system prompt hit the prompt cache. The ``anthropic`` SDK is imported lazily
so the app still imports in environments where it (or an API key) is absent.
"""
from __future__ import annotations

import json

from app.config import settings


def is_available() -> bool:
    """True when an Anthropic API key is configured."""
    return bool(settings.ANTHROPIC_API_KEY)


async def complete(
    system: str,
    messages: list[dict],
    max_tokens: int = 700,
    tools: list[dict] | None = None,
) -> dict:
    """
    Call Claude once. Returns ``{"text", "tool_use", "stop_reason"}``.

    Raises ``RuntimeError`` if no API key is configured — callers that want a
    graceful fallback should check ``is_available()`` first.
    """
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured.")

    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    kwargs: dict = {
        "model": settings.ANTHROPIC_MODEL,
        "max_tokens": max_tokens,
        # List form + cache_control enables prompt caching of the system prompt.
        "system": [
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
        ],
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools

    resp = await client.messages.create(**kwargs)
    text = "".join(b.text for b in resp.content if b.type == "text")
    tool_use = [
        {"id": b.id, "name": b.name, "input": b.input}
        for b in resp.content
        if b.type == "tool_use"
    ]
    return {"text": text, "tool_use": tool_use, "stop_reason": resp.stop_reason}


def extract_json(text: str) -> dict | list | None:
    """Best-effort JSON extraction from a model response."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
    start = min(
        (i for i in (text.find("{"), text.find("[")) if i != -1), default=-1
    )
    if start == -1:
        return None
    try:
        # raw_decode parses the first JSON value and ignores any trailing text.
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
        return obj
    except json.JSONDecodeError:
        return None
