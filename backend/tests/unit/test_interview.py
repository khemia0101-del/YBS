"""AI interviewer tests — exercise the scripted fallback (no API key)."""
from __future__ import annotations

import pytest

from app.services.ai import llm_client
from app.services.interview.ai_interviewer import next_question
from app.services.interview.analysis import extract_insights


@pytest.mark.asyncio
async def test_owner_interview_opens_with_first_scripted_question():
    result = await next_question("owner", [])
    assert result["complete"] is False
    assert result["source"] == "scripted"  # no ANTHROPIC_API_KEY in tests
    assert "what does the business do" in result["question"].lower()


@pytest.mark.asyncio
async def test_interview_completes_after_question_budget():
    history: list[dict] = []
    seen = 0
    for _ in range(12):
        q = await next_question("owner", history)
        history.append({"sender": "assistant", "content": q["question"]})
        if q["complete"]:
            break
        history.append({"sender": "interviewee", "content": "An answer."})
        seen += 1
    assert seen >= 7  # owner script asks ~8 questions
    assert q["complete"] is True


@pytest.mark.asyncio
async def test_employee_script_differs_from_owner():
    owner = await next_question("owner", [])
    employee = await next_question("employee", [])
    assert owner["question"] != employee["question"]


@pytest.mark.asyncio
async def test_extract_insights_empty_history():
    assert await extract_insights([]) == []


@pytest.mark.asyncio
async def test_extract_insights_fallback_without_api_key():
    history = [
        {"sender": "assistant", "content": "What does the business do?"},
        {"sender": "interviewee", "content": "We repair credit."},
    ]
    insights = await extract_insights(history)
    assert len(insights) == 1
    assert insights[0]["insight_type"] == "operations_map"


def test_extract_json_handles_fenced_blocks():
    assert llm_client.extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert llm_client.extract_json('prose then {"b": 2} trailing') == {"b": 2}
    assert llm_client.extract_json("no json here") is None
