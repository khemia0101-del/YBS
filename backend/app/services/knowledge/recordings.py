"""
Meeting-recording ingester.

Accepts an uploaded transcript in plain text, VTT, SRT or JSON. Parses speakers
and turns into a normalized transcript string the chunker can handle. Audio
transcription from raw recordings is a follow-up; this round expects a
transcript file.
"""
from __future__ import annotations

import json
import re
from datetime import datetime

_VTT_TIMECODE_RE = re.compile(
    r"^\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[.,]\d{3}.*$"
)
_SRT_INDEX_RE = re.compile(r"^\d+$")
_VTT_SPEAKER_RE = re.compile(r"<v\s+([^>]+)>(.*?)(?:</v>|$)", re.DOTALL)
_LINE_SPEAKER_RE = re.compile(r"^\s*([A-Za-z][\w .'-]{1,40})\s*[:\-]\s+(.*)$")


def parse_transcript(payload: str, filename: str | None = None) -> dict:
    """
    Parse a transcript into ``{"format", "title", "content", "turns",
    "started_at"}``. ``turns`` is a list of ``{"speaker", "text"}``. ``content``
    is a human-readable normalized version suitable for chunking.
    """
    text = (payload or "").strip()
    if not text:
        raise ValueError("Empty transcript.")

    fmt = _detect_format(text, filename)
    if fmt == "json":
        parsed = _parse_json(text)
    elif fmt == "vtt":
        parsed = _parse_vtt(text)
    elif fmt == "srt":
        parsed = _parse_srt(text)
    else:
        parsed = _parse_plain(text)

    parsed["format"] = fmt
    if not parsed.get("title"):
        parsed["title"] = filename or "Meeting transcript"
    if not parsed.get("content"):
        parsed["content"] = _render(parsed["turns"])
    return parsed


def _detect_format(text: str, filename: str | None) -> str:
    if filename:
        lower = filename.lower()
        for ext, fmt in (
            (".vtt", "vtt"),
            (".srt", "srt"),
            (".json", "json"),
        ):
            if lower.endswith(ext):
                return fmt
    stripped = text.lstrip()
    if stripped.startswith("WEBVTT"):
        return "vtt"
    if stripped.startswith("{") or stripped.startswith("["):
        return "json"
    if _SRT_INDEX_RE.match(stripped.splitlines()[0] or ""):
        return "srt"
    return "txt"


def _parse_json(text: str) -> dict:
    raw = json.loads(text)
    turns: list[dict] = []
    title = None
    started_at = None
    if isinstance(raw, dict):
        title = raw.get("title") or raw.get("name")
        started_at = raw.get("started_at") or raw.get("date")
        items = (
            raw.get("turns")
            or raw.get("segments")
            or raw.get("transcript")
            or raw.get("entries")
            or []
        )
    else:
        items = raw
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        speaker = item.get("speaker") or item.get("name") or item.get("from") or "Speaker"
        body = item.get("text") or item.get("content") or item.get("body") or ""
        if body:
            turns.append({"speaker": str(speaker).strip(), "text": str(body).strip()})
    return {"title": title, "started_at": started_at, "turns": turns, "content": None}


def _parse_vtt(text: str) -> dict:
    turns: list[dict] = []
    current_speaker = "Speaker"
    current_text: list[str] = []
    for raw in text.splitlines()[1:]:  # skip "WEBVTT" header
        line = raw.strip()
        if not line or _VTT_TIMECODE_RE.match(line) or line.startswith("NOTE"):
            if current_text:
                turns.append(
                    {"speaker": current_speaker, "text": " ".join(current_text).strip()}
                )
                current_text = []
            continue
        m = _VTT_SPEAKER_RE.search(line)
        if m:
            current_speaker = m.group(1).strip() or current_speaker
            line = m.group(2).strip()
        if line:
            current_text.append(line)
    if current_text:
        turns.append(
            {"speaker": current_speaker, "text": " ".join(current_text).strip()}
        )
    return {"title": None, "started_at": None, "turns": turns, "content": None}


def _parse_srt(text: str) -> dict:
    turns: list[dict] = []
    current_text: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or _SRT_INDEX_RE.match(line) or _VTT_TIMECODE_RE.match(line):
            if current_text:
                turns.append(
                    {"speaker": "Speaker", "text": " ".join(current_text).strip()}
                )
                current_text = []
            continue
        current_text.append(line)
    if current_text:
        turns.append({"speaker": "Speaker", "text": " ".join(current_text).strip()})
    return {"title": None, "started_at": None, "turns": turns, "content": None}


def _parse_plain(text: str) -> dict:
    turns: list[dict] = []
    current_speaker = "Speaker"
    current_text: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            if current_text:
                turns.append(
                    {"speaker": current_speaker, "text": " ".join(current_text).strip()}
                )
                current_text = []
            continue
        m = _LINE_SPEAKER_RE.match(line)
        if m:
            if current_text:
                turns.append(
                    {"speaker": current_speaker, "text": " ".join(current_text).strip()}
                )
                current_text = []
            current_speaker = m.group(1).strip()
            line = m.group(2).strip()
        current_text.append(line)
    if current_text:
        turns.append(
            {"speaker": current_speaker, "text": " ".join(current_text).strip()}
        )
    return {"title": None, "started_at": None, "turns": turns, "content": None}


def _render(turns: list[dict]) -> str:
    return "\n".join(f"{t['speaker']}: {t['text']}" for t in turns if t.get("text"))


def derive_title(parsed: dict, fallback: str | None = None) -> str:
    title = parsed.get("title") or fallback
    if title:
        return str(title).strip()[:200]
    return f"Meeting transcript {datetime.utcnow().date().isoformat()}"
