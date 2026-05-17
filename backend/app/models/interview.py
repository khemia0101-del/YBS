"""
AI conversational interview.

An InterviewSession is a chat with a business owner or employee. It does
double duty: onboarding discovery (inferring the BusinessProfile) and
operations mapping (surfacing pain points and automation opportunities).
Extracted findings are stored as InterviewInsight rows.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class InterviewSession(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_sessions"

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # owner | employee
    interviewee_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    interviewee_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    # onboarding | operations
    purpose: Mapped[str] = mapped_column(String(20), nullable=False, default="operations")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    messages: Mapped[list[InterviewMessage]] = relationship(
        "InterviewMessage", back_populates="session"
    )
    insights: Mapped[list[InterviewInsight]] = relationship(
        "InterviewInsight", back_populates="session"
    )


class InterviewMessage(Base, UUIDMixin):
    __tablename__ = "interview_messages"

    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("interview_sessions.id"), nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    sender: Mapped[str] = mapped_column(String(20), nullable=False)  # assistant | interviewee
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped[InterviewSession] = relationship(
        "InterviewSession", back_populates="messages"
    )


class InterviewInsight(Base, UUIDMixin):
    __tablename__ = "interview_insights"

    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("interview_sessions.id"), nullable=False
    )
    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    # operations_map | pain_point | automation_opportunity | proposed_profile
    insight_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped[InterviewSession] = relationship(
        "InterviewSession", back_populates="insights"
    )
