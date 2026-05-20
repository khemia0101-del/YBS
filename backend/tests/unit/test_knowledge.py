"""Company brain (Phase 10) — chunker, ingest, retriever, recordings."""
from __future__ import annotations

import uuid

import pytest

from app.models.interview import InterviewMessage, InterviewSession
from app.services.knowledge import recordings
from app.services.knowledge.chunker import chunk_text, estimate_tokens
from app.services.knowledge.ingest import (
    ingest_document,
    ingest_interview_session,
    reindex_company,
)
from app.services.knowledge.retriever import format_chunks_for_prompt, retrieve


def test_chunker_returns_single_chunk_for_short_text():
    chunks = chunk_text("Hello world.")
    assert chunks == ["Hello world."]


def test_chunker_splits_on_paragraphs():
    paragraphs = [f"Para {i}: " + ("lorem ipsum " * 80) for i in range(6)]
    text = "\n\n".join(paragraphs)
    chunks = chunk_text(text, max_chars=1000, overlap_chars=0)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 1200


def test_chunker_respects_max_chars_with_long_paragraph():
    text = "x" * 12000
    chunks = chunk_text(text, max_chars=1000, overlap_chars=0)
    assert len(chunks) >= 12


def test_estimate_tokens_returns_positive():
    assert estimate_tokens("hello world") > 0


@pytest.mark.asyncio
async def test_ingest_document_creates_chunks(db_session, sample_company):
    result = await ingest_document(
        db=db_session,
        company_id=sample_company.id,
        source_type="upload",
        source_ref="test-1",
        title="Test doc",
        content=("Quarterly revenue grew by 12 percent. " * 200),
    )
    assert result["chunks"] >= 1
    assert result["changed"] is True

    # Idempotent re-upsert with the same content does not mark changed.
    again = await ingest_document(
        db=db_session,
        company_id=sample_company.id,
        source_type="upload",
        source_ref="test-1",
        title="Test doc",
        content=("Quarterly revenue grew by 12 percent. " * 200),
    )
    assert again["changed"] is False
    assert again["document_id"] == result["document_id"]


@pytest.mark.asyncio
async def test_retriever_keyword_fallback(
    db_session, sample_company, sample_tenant
):
    await ingest_document(
        db=db_session,
        company_id=sample_company.id,
        source_type="upload",
        source_ref="r1",
        title="Pricing notes",
        content="The enrollment fee should rise to 199 dollars.",
    )
    await ingest_document(
        db=db_session,
        company_id=sample_company.id,
        source_type="upload",
        source_ref="r2",
        title="Logo brainstorm",
        content="We argued for two hours about font weight.",
    )
    results = await retrieve(
        db_session, sample_tenant.id, sample_company.id, "enrollment fee pricing"
    )
    assert results
    assert results[0]["title"] == "Pricing notes"


@pytest.mark.asyncio
async def test_retriever_filters_by_tenant(db_session, sample_tenant, sample_company):
    """Searching with a different tenant_id must not return this company's chunks."""
    await ingest_document(
        db=db_session,
        company_id=sample_company.id,
        source_type="upload",
        source_ref="x",
        title="Confidential pricing",
        content="The deal terms include enrollment fees of one hundred ninety nine.",
    )
    other_tenant_id = uuid.uuid4()
    results = await retrieve(
        db_session, other_tenant_id, None, "enrollment fee pricing"
    )
    assert results == []


@pytest.mark.asyncio
async def test_retriever_format_chunks_for_prompt(
    db_session, sample_tenant, sample_company
):
    await ingest_document(
        db=db_session,
        company_id=sample_company.id,
        source_type="upload",
        source_ref="q",
        title="Quarterly review",
        content="Margins improved 4 points last quarter.",
    )
    results = await retrieve(
        db_session, sample_tenant.id, sample_company.id, "margins quarter"
    )
    rendered = format_chunks_for_prompt(results)
    assert "Quarterly review" in rendered


def test_recordings_parse_plain_with_speakers():
    text = """Alice: Welcome everyone.
Bob: Thanks for joining.

Alice: Let's discuss Q4."""
    parsed = recordings.parse_transcript(text, filename="meeting.txt")
    assert parsed["format"] == "txt"
    assert len(parsed["turns"]) >= 2
    assert parsed["turns"][0]["speaker"] == "Alice"


def test_recordings_parse_vtt():
    text = """WEBVTT

00:00:00.000 --> 00:00:05.000
<v Alice>Hello team

00:00:05.000 --> 00:00:08.000
<v Bob>Hi Alice"""
    parsed = recordings.parse_transcript(text, filename="meeting.vtt")
    assert parsed["format"] == "vtt"
    assert any(t["speaker"] == "Alice" for t in parsed["turns"])


def test_recordings_parse_json():
    text = (
        '{"title":"Investor call","turns":[{"speaker":"GP","text":"hello"},'
        '{"speaker":"LP","text":"hi"}]}'
    )
    parsed = recordings.parse_transcript(text, filename="x.json")
    assert parsed["format"] == "json"
    assert parsed["title"] == "Investor call"
    assert len(parsed["turns"]) == 2


@pytest.mark.asyncio
async def test_ingest_interview_session(db_session, sample_company):
    session = InterviewSession(
        id=uuid.uuid4(),
        company_id=sample_company.id,
        role="owner",
        interviewee_name="Pat Owner",
        purpose="onboarding",
        status="completed",
    )
    db_session.add(session)
    await db_session.flush()
    for i, line in enumerate(["What do you do?", "Credit repair, mostly."]):
        db_session.add(
            InterviewMessage(
                id=uuid.uuid4(),
                session_id=session.id,
                seq=i + 1,
                sender="assistant" if i % 2 == 0 else "interviewee",
                content=line,
            )
        )
    await db_session.flush()
    result = await ingest_interview_session(db_session, session.id)
    assert result is not None
    assert result["chunks"] >= 1


@pytest.mark.asyncio
async def test_reindex_company_runs(db_session, sample_company):
    out = await reindex_company(db_session, sample_company.id)
    assert "counts" in out
    assert isinstance(out["counts"], dict)
