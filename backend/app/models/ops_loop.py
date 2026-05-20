"""
Continuous ops loops — recurring agents that re-analyze the business and
queue proposed actions through the existing CooAction approval flow.

An OpsLoop is a configurable, scheduled agent (e.g. "weekly funnel review"
or "daily cash health watch"). Each run builds a fresh business briefing
plus retrieved company-brain context, asks Claude for a focused analysis,
and lets Claude propose 0-N CooActions — none of which execute until the
owner approves them.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class OpsLoop(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "ops_loops"

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    # funnel | cash | churn | metrics | support | custom
    focus: Mapped[str] = mapped_column(String(20), nullable=False, default="metrics")
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    schedule_cron: Mapped[str] = mapped_column(
        Text, nullable=False, default="0 9 * * 1"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    runs: Mapped[list[OpsLoopRun]] = relationship(
        "OpsLoopRun", back_populates="loop"
    )


class OpsLoopRun(Base, UUIDMixin):
    __tablename__ = "ops_loop_runs"

    loop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ops_loops.id", ondelete="CASCADE"),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # running | succeeded | failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    findings_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_actions_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    loop: Mapped[OpsLoop] = relationship("OpsLoop", back_populates="runs")
