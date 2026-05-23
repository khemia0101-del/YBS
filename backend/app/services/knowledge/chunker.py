"""
Paragraph-aware text splitter.

Targets roughly ``max_chars`` per chunk, preferring paragraph breaks then
sentence breaks then hard cuts. A rough heuristic of 4 chars per token is used
to set defaults around 1k tokens.
"""
from __future__ import annotations

import re

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n+")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_DEFAULT_MAX_CHARS = 4000
_DEFAULT_OVERLAP_CHARS = 200


def chunk_text(
    text: str,
    max_chars: int = _DEFAULT_MAX_CHARS,
    overlap_chars: int = _DEFAULT_OVERLAP_CHARS,
) -> list[str]:
    """Split ``text`` into reasonably-sized chunks."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT.split(text) if p.strip()]
    chunks: list[str] = []
    buf = ""

    def flush() -> None:
        nonlocal buf
        if buf.strip():
            chunks.append(buf.strip())
        buf = ""

    for para in paragraphs:
        if len(para) > max_chars:
            flush()
            for piece in _split_long(para, max_chars):
                chunks.append(piece)
            continue
        if not buf:
            buf = para
        elif len(buf) + 2 + len(para) <= max_chars:
            buf = f"{buf}\n\n{para}"
        else:
            flush()
            buf = para
    flush()

    if overlap_chars > 0 and len(chunks) > 1:
        chunks = _add_overlap(chunks, overlap_chars)
    return chunks


def _split_long(text: str, max_chars: int) -> list[str]:
    """Split a paragraph longer than ``max_chars`` along sentence boundaries."""
    sentences = _SENTENCE_SPLIT.split(text)
    out: list[str] = []
    buf = ""
    for sent in sentences:
        if len(sent) > max_chars:
            if buf:
                out.append(buf.strip())
                buf = ""
            for i in range(0, len(sent), max_chars):
                out.append(sent[i : i + max_chars])
            continue
        if not buf:
            buf = sent
        elif len(buf) + 1 + len(sent) <= max_chars:
            buf = f"{buf} {sent}"
        else:
            out.append(buf.strip())
            buf = sent
    if buf.strip():
        out.append(buf.strip())
    return out


def _add_overlap(chunks: list[str], overlap_chars: int) -> list[str]:
    """Glue a small trailing slice of each chunk onto the next, for context bleed."""
    out = [chunks[0]]
    for i in range(1, len(chunks)):
        prev_tail = chunks[i - 1][-overlap_chars:]
        out.append(f"{prev_tail}\n\n{chunks[i]}")
    return out


def estimate_tokens(text: str) -> int:
    """Cheap token estimate — ~4 chars per token."""
    return max(1, len(text) // 4)
