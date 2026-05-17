"""
Automation roadmap.

An AutomationItem is one candidate process to automate, scored by impact and
effort. Items come from interview insights and from observed data patterns.
A dispatched item is linked to an AgentTask routed through the approval queue.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class AutomationItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "automation_items"
    __table_args__ = (
        UniqueConstraint("company_id", "title", name="uq_automation_company_title"),
    )

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # "interview" | "observed"
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="observed")
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    effort: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    priority_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # "proposed" | "dispatched" | "done" | "dismissed"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="proposed")
    agent_task_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
