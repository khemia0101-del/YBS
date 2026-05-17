"""
AI conversational interviewer.

Conducts an adaptive interview with a business owner or employee. When an
Anthropic key is configured it uses Claude to ask context-aware follow-ups;
otherwise it falls back to a fixed, role-aware question script so the feature
still works end-to-end.
"""
from __future__ import annotations

from app.services.ai import llm_client

_OWNER_SCRIPT = [
    "Thanks for taking the time. In your own words — what does the business do, "
    "and who are your customers?",
    "Walk me through what happens from when a new customer signs up to when they're "
    "fully served. What are the main steps?",
    "Which of those steps takes the most time or causes the most headaches?",
    "What does a typical week look like for you and your team — who does what?",
    "Where do new customers come from today, and roughly how many do you get a month?",
    "What numbers do you watch to know the business is healthy?",
    "If you could wave a magic wand and have one thing handled automatically, "
    "what would it be?",
    "Last one — what would have to be true for the business to grow substantially "
    "this year?",
]

_EMPLOYEE_SCRIPT = [
    "Thanks for chatting. What's your role, and what are you responsible for day to day?",
    "Walk me through a normal day — which tasks do you repeat the most?",
    "Which parts of your job are the most tedious or repetitive?",
    "Where do things tend to get stuck, or where do mistakes usually happen?",
    "What tools or systems do you use? Anything that slows you down?",
    "If part of your job could be done automatically, what would you pick?",
    "Anything you think the business should do differently?",
]

_SYSTEM = """You are an experienced operations consultant running a friendly, adaptive \
interview with the {role} of a small business. Goals: understand how the business really \
runs, surface pain points, and spot opportunities to automate or improve.

Rules:
- Ask ONE clear, conversational question at a time. No preamble, no bullet lists.
- Build on what the person just said — follow the thread; ask for specifics and numbers.
- Keep it short and plain; the interviewee is non-technical.
- This is question {n} of about {budget}. If n is at or past the budget, ask a brief \
final wrap-up question only.
Return only the question text."""


def _script(role: str) -> list[str]:
    return _OWNER_SCRIPT if role == "owner" else _EMPLOYEE_SCRIPT


def _budget(role: str) -> int:
    return 8 if role == "owner" else 7


async def next_question(role: str, history: list[dict]) -> dict:
    """
    Produce the next interview question.

    ``history`` is the ordered conversation: ``{"sender": "assistant"|"interviewee",
    "content": str}``. Returns ``{"question", "source", "complete"}``.
    """
    asked = sum(1 for m in history if m["sender"] == "assistant")
    budget = _budget(role)
    n = asked + 1

    if not llm_client.is_available():
        script = _script(role)
        if asked < len(script):
            return {"question": script[asked], "source": "scripted", "complete": False}
        return {
            "question": "Thank you — that's everything I needed for now.",
            "source": "scripted",
            "complete": True,
        }

    messages = [
        {
            "role": "assistant" if m["sender"] == "assistant" else "user",
            "content": m["content"],
        }
        for m in history
    ]
    if not messages:
        messages = [{"role": "user", "content": "Please begin the interview."}]

    result = await llm_client.complete(
        _SYSTEM.format(role=role, n=n, budget=budget), messages, max_tokens=300
    )
    return {
        "question": result["text"].strip(),
        "source": "ai",
        "complete": n > budget,
    }
