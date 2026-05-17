"""AI COO — conversational executive assistant + pending-action approval tray."""
from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import assert_company_in_tenant, get_tenant_id, require_analyst
from app.models.coo import CooAction, CooConversation, CooMessage
from app.models.users import User
from app.schemas.coo import (
    ConversationResponse,
    CooActionResponse,
    CooMessageResponse,
    SendMessageRequest,
)
from app.services.coo.actions import execute_action
from app.services.coo.assistant import converse

router = APIRouter()


async def _load_conversation(
    db: AsyncSession, conversation_id: UUID, tenant_id: UUID
) -> CooConversation:
    result = await db.execute(
        select(CooConversation).where(CooConversation.id == conversation_id)
    )
    convo = result.scalar_one_or_none()
    if convo is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await assert_company_in_tenant(db, convo.company_id, tenant_id)
    return convo


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    company_id: UUID = Query(...),
    title: str = Query("New conversation"),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> ConversationResponse:
    await assert_company_in_tenant(db, company_id, tenant_id)
    convo = CooConversation(
        id=uuid.uuid4(), company_id=company_id, title=title, status="active"
    )
    db.add(convo)
    await db.flush()
    return ConversationResponse.model_validate(convo)


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    company_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> list[ConversationResponse]:
    await assert_company_in_tenant(db, company_id, tenant_id)
    result = await db.execute(
        select(CooConversation)
        .where(CooConversation.company_id == company_id)
        .order_by(CooConversation.created_at.desc())
    )
    return [ConversationResponse.model_validate(c) for c in result.scalars().all()]


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> dict:
    convo = await _load_conversation(db, conversation_id, tenant_id)
    msgs = await db.execute(
        select(CooMessage)
        .where(CooMessage.conversation_id == conversation_id)
        .order_by(CooMessage.seq)
    )
    return {
        "conversation": ConversationResponse.model_validate(convo).model_dump(mode="json"),
        "messages": [
            CooMessageResponse.model_validate(m).model_dump()
            for m in msgs.scalars().all()
        ],
    }


@router.post("/conversations/{conversation_id}/message")
async def send_message(
    conversation_id: UUID,
    body: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> dict:
    """Send a message to the COO and get its reply plus any proposed actions."""
    convo = await _load_conversation(db, conversation_id, tenant_id)

    seq_result = await db.execute(
        select(func.coalesce(func.max(CooMessage.seq), 0)).where(
            CooMessage.conversation_id == conversation_id
        )
    )
    seq = (seq_result.scalar() or 0) + 1
    db.add(
        CooMessage(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            seq=seq,
            role="user",
            content=body.message,
        )
    )

    history_result = await db.execute(
        select(CooMessage)
        .where(CooMessage.conversation_id == conversation_id)
        .order_by(CooMessage.seq)
    )
    history = [
        {"role": m.role, "content": m.content}
        for m in history_result.scalars().all()
    ]

    try:
        outcome = await converse(db, convo.company_id, history, body.message)
    except Exception as exc:  # noqa: BLE001 — surface AI/service errors cleanly
        raise HTTPException(status_code=502, detail=f"AI service error: {exc}")

    db.add(
        CooMessage(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            seq=seq + 1,
            role="assistant",
            content=outcome["reply"],
        )
    )

    actions: list[CooAction] = []
    for pa in outcome["proposed_actions"]:
        action = CooAction(
            id=uuid.uuid4(),
            company_id=convo.company_id,
            conversation_id=conversation_id,
            action_type=pa["action_type"],
            title=pa["title"],
            payload=pa["payload"],
            status="pending",
        )
        db.add(action)
        actions.append(action)
    await db.flush()

    return {
        "reply": outcome["reply"],
        "proposed_actions": [
            CooActionResponse.model_validate(a).model_dump(mode="json")
            for a in actions
        ],
    }


@router.get("/actions", response_model=list[CooActionResponse])
async def list_actions(
    company_id: UUID = Query(...),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
) -> list[CooActionResponse]:
    await assert_company_in_tenant(db, company_id, tenant_id)
    q = select(CooAction).where(CooAction.company_id == company_id)
    if status:
        q = q.where(CooAction.status == status)
    result = await db.execute(q.order_by(CooAction.created_at.desc()))
    return [CooActionResponse.model_validate(a) for a in result.scalars().all()]


async def _load_action(
    db: AsyncSession, action_id: UUID, tenant_id: UUID
) -> CooAction:
    result = await db.execute(select(CooAction).where(CooAction.id == action_id))
    action = result.scalar_one_or_none()
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    await assert_company_in_tenant(db, action.company_id, tenant_id)
    return action


@router.post("/actions/{action_id}/approve", response_model=CooActionResponse)
async def approve_action(
    action_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user: User = Depends(require_analyst),
) -> CooActionResponse:
    """Approve a COO action — and only now execute it."""
    action = await _load_action(db, action_id, tenant_id)
    if action.status != "pending":
        raise HTTPException(status_code=409, detail=f"Action is '{action.status}'")
    action.status = "approved"
    await execute_action(db, action)
    return CooActionResponse.model_validate(action)


@router.post("/actions/{action_id}/reject", response_model=CooActionResponse)
async def reject_action(
    action_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    _user: User = Depends(require_analyst),
) -> CooActionResponse:
    action = await _load_action(db, action_id, tenant_id)
    if action.status != "pending":
        raise HTTPException(status_code=409, detail=f"Action is '{action.status}'")
    action.status = "rejected"
    await db.flush()
    return CooActionResponse.model_validate(action)
