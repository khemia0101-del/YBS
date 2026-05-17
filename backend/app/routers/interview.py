"""AI conversational interview — tenant-scoped session + chat endpoints."""
from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import assert_company_in_tenant, get_tenant_id
from app.models.interview import InterviewInsight, InterviewMessage, InterviewSession
from app.schemas.interview import (
    AnswerRequest,
    InsightResponse,
    InterviewSessionCreate,
    InterviewSessionResponse,
    MessageResponse,
)
from app.services.interview.ai_interviewer import next_question
from app.services.interview.analysis import extract_insights

router = APIRouter()


async def _load_session(
    db: AsyncSession, session_id: UUID, tenant_id: UUID
) -> InterviewSession:
    result = await db.execute(
        select(InterviewSession).where(InterviewSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Interview session not found")
    await assert_company_in_tenant(db, session.company_id, tenant_id)
    return session


async def _history(db: AsyncSession, session_id: UUID) -> list[dict]:
    result = await db.execute(
        select(InterviewMessage)
        .where(InterviewMessage.session_id == session_id)
        .order_by(InterviewMessage.seq)
    )
    return [
        {"sender": m.sender, "content": m.content} for m in result.scalars().all()
    ]


async def _next_seq(db: AsyncSession, session_id: UUID) -> int:
    result = await db.execute(
        select(func.coalesce(func.max(InterviewMessage.seq), 0)).where(
            InterviewMessage.session_id == session_id
        )
    )
    return (result.scalar() or 0) + 1


@router.post("/sessions")
async def create_session(
    body: InterviewSessionCreate,
    company_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> dict:
    """Start an interview and return the opening question."""
    await assert_company_in_tenant(db, company_id, tenant_id)
    role = body.role if body.role in ("owner", "employee") else "owner"

    session = InterviewSession(
        id=uuid.uuid4(),
        company_id=company_id,
        role=role,
        interviewee_name=body.interviewee_name,
        interviewee_email=body.interviewee_email,
        purpose=body.purpose,
        status="active",
    )
    db.add(session)
    await db.flush()

    try:
        opening = await next_question(role, [])
    except Exception as exc:  # noqa: BLE001 — surface AI/service errors cleanly
        raise HTTPException(status_code=502, detail=f"AI service error: {exc}")

    db.add(
        InterviewMessage(
            id=uuid.uuid4(),
            session_id=session.id,
            seq=1,
            sender="assistant",
            content=opening["question"],
        )
    )
    await db.flush()
    return {
        "session": InterviewSessionResponse.model_validate(session).model_dump(mode="json"),
        "question": opening["question"],
        "complete": opening["complete"],
    }


@router.get("/sessions", response_model=list[InterviewSessionResponse])
async def list_sessions(
    company_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> list[InterviewSessionResponse]:
    await assert_company_in_tenant(db, company_id, tenant_id)
    result = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.company_id == company_id)
        .order_by(InterviewSession.created_at.desc())
    )
    return [InterviewSessionResponse.model_validate(s) for s in result.scalars().all()]


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> dict:
    session = await _load_session(db, session_id, tenant_id)
    msgs_result = await db.execute(
        select(InterviewMessage)
        .where(InterviewMessage.session_id == session_id)
        .order_by(InterviewMessage.seq)
    )
    messages = [MessageResponse.model_validate(m) for m in msgs_result.scalars().all()]
    return {
        "session": InterviewSessionResponse.model_validate(session).model_dump(mode="json"),
        "messages": [m.model_dump() for m in messages],
    }


@router.post("/sessions/{session_id}/answer")
async def submit_answer(
    session_id: UUID,
    body: AnswerRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> dict:
    """Record the interviewee's answer and return the next question."""
    session = await _load_session(db, session_id, tenant_id)
    if session.status != "active":
        raise HTTPException(status_code=409, detail="Interview is already completed")

    seq = await _next_seq(db, session_id)
    db.add(
        InterviewMessage(
            id=uuid.uuid4(),
            session_id=session_id,
            seq=seq,
            sender="interviewee",
            content=body.answer,
        )
    )
    await db.flush()

    history = await _history(db, session_id)
    try:
        result = await next_question(session.role, history)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"AI service error: {exc}")

    db.add(
        InterviewMessage(
            id=uuid.uuid4(),
            session_id=session_id,
            seq=seq + 1,
            sender="assistant",
            content=result["question"],
        )
    )
    await db.flush()
    return {"question": result["question"], "complete": result["complete"]}


@router.post("/sessions/{session_id}/complete")
async def complete_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> dict:
    """Finalize the interview: extract insights and store them."""
    session = await _load_session(db, session_id, tenant_id)
    history = await _history(db, session_id)
    try:
        insights = await extract_insights(history)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"AI service error: {exc}")

    stored: list[InterviewInsight] = []
    for ins in insights:
        row = InterviewInsight(
            id=uuid.uuid4(),
            session_id=session_id,
            company_id=session.company_id,
            insight_type=ins["insight_type"],
            title=ins["title"],
            content=ins.get("content"),
        )
        db.add(row)
        stored.append(row)
    session.status = "completed"
    await db.flush()
    return {
        "session_id": str(session_id),
        "status": "completed",
        "insights": [InsightResponse.model_validate(i).model_dump(mode="json") for i in stored],
    }


@router.get("/sessions/{session_id}/insights", response_model=list[InsightResponse])
async def list_insights(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> list[InsightResponse]:
    await _load_session(db, session_id, tenant_id)
    result = await db.execute(
        select(InterviewInsight)
        .where(InterviewInsight.session_id == session_id)
        .order_by(InterviewInsight.created_at)
    )
    return [InsightResponse.model_validate(i) for i in result.scalars().all()]
