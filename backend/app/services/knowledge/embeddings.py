"""
Embeddings provider — Voyage AI when configured, otherwise off.

Callers should always check ``is_available()`` first. When embeddings are not
available the retriever falls back to keyword scoring, so the rest of the
system still works.
"""
from __future__ import annotations

from app.config import settings

_DEFAULT_MODEL = "voyage-3"


def is_available() -> bool:
    return bool(getattr(settings, "VOYAGE_API_KEY", ""))


async def embed(texts: list[str], input_type: str = "document") -> list[list[float]]:
    """Return embedding vectors for ``texts``. Raises if no provider configured."""
    if not is_available():
        raise RuntimeError("VOYAGE_API_KEY is not configured.")
    if not texts:
        return []

    import voyageai  # type: ignore[import-not-found]

    client = voyageai.AsyncClient(api_key=settings.VOYAGE_API_KEY)
    result = await client.embed(
        texts,
        model=getattr(settings, "VOYAGE_MODEL", _DEFAULT_MODEL),
        input_type=input_type,
    )
    return [list(v) for v in result.embeddings]


async def embed_one(text: str, input_type: str = "query") -> list[float]:
    vectors = await embed([text], input_type=input_type)
    return vectors[0] if vectors else []
