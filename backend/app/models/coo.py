"""
AI COO — conversational executive assistant.

The owner chats with the COO (CooConversation / CooMessage). When the COO wants
to act, it does not act directly: it creates a CooAction in "pending" status.
The owner approves with one tap; only then is the action executed — sending an
EmployeeMessage (email) or creating an EmployeeTask (in-app assignment).
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class CooConversation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "coo_conversations"

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False, default="New conversation")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    messages: Mapped[list[CooMessage]] = relationship(
        "CooMessage", back_populates="conversation"
    )


class CooMessage(Base, UUIDMixin):
    __tablename__ = "coo_messages"

    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("coo_conversations.id"), nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation: Mapped[CooConversation] = relationship(
        "CooConversation", back_populates="messages"
    )


class CooAction(Base, UUIDMixin, TimestampMixin):
    """A COO-proposed action awaiting the owner's one-tap approval."""

    __tablename__ = "coo_actions"

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("coo_conversations.id"), nullable=True
    )
    # employee_email | employee_task | business_change
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    # pending | approved | rejected | executed | failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class EmployeeTask(Base, UUIDMixin, TimestampMixin):
    """An in-app task assigned to an employee — created when a CooAction is approved."""

    __tablename__ = "employee_tasks"

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assignee_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    assignee_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    source_action_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )


class EmployeeMessage(Base, UUIDMixin):
    """A log of an outbound email to an employee — sent when a CooAction is approved."""

    __tablename__ = "employee_messages"

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    to_email: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="sent")
    source_action_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
