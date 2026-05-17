"""
Interview analysis.

After an interview completes, extracts a structured operations map, pain points,
ranked automation opportunities, and a proposed business profile from the
transcript. Each finding becomes an InterviewInsight row.
"""
from __future__ import annotations

from app.services.ai import llm_client

_ANALYSIS_SYSTEM = """You analyze a small-business interview transcript and extract \
structured findings. Respond with ONLY a JSON object, no prose, of this shape:

{
  "operations_summary": "2-3 sentence summary of how the business operates",
  "pain_points": [{"title": "...", "detail": "...", "severity": "low|medium|high"}],
  "automation_opportunities": [
    {"title": "...", "detail": "...", "impact": "low|medium|high", "effort": "low|medium|high"}
  ],
  "proposed_profile": {
    "industry": "...", "business_model": "...",
    "suggested_metrics": ["metric name", ...]
  }
}
Be concrete and specific to what the transcript actually says."""


def _transcript(history: list[dict]) -> str:
    return "\n\n".join(
        f"{'Interviewer' if m['sender'] == 'assistant' else 'Interviewee'}: {m['content']}"
        for m in history
    )


def _fallback(history: list[dict]) -> list[dict]:
    return [
        {
            "insight_type": "operations_map",
            "title": "Interview transcript captured",
            "content": {
                "note": "Structured AI analysis requires ANTHROPIC_API_KEY; "
                "the transcript has been stored for manual review.",
                "message_count": len(history),
            },
        }
    ]


async def extract_insights(history: list[dict]) -> list[dict]:
    """Return a list of insight dicts: ``{insight_type, title, content}``."""
    if not history:
        return []
    if not llm_client.is_available():
        return _fallback(history)

    result = await llm_client.complete(
        _ANALYSIS_SYSTEM,
        [
            {
                "role": "user",
                "content": f"Interview transcript:\n\n{_transcript(history)}",
            }
        ],
        max_tokens=2000,
    )
    data = llm_client.extract_json(result["text"])
    if not isinstance(data, dict):
        return _fallback(history)

    insights: list[dict] = []
    if data.get("operations_summary"):
        insights.append(
            {
                "insight_type": "operations_map",
                "title": "Operations summary",
                "content": {"summary": data["operations_summary"]},
            }
        )
    for pp in data.get("pain_points", []):
        insights.append(
            {
                "insight_type": "pain_point",
                "title": pp.get("title", "Pain point"),
                "content": pp,
            }
        )
    for opp in data.get("automation_opportunities", []):
        insights.append(
            {
                "insight_type": "automation_opportunity",
                "title": opp.get("title", "Automation opportunity"),
                "content": opp,
            }
        )
    if data.get("proposed_profile"):
        insights.append(
            {
                "insight_type": "proposed_profile",
                "title": "Proposed business profile",
                "content": data["proposed_profile"],
            }
        )
    return insights or _fallback(history)
