"""
Self-improving monitor — observation + diagnosis records.

Collectors continuously scan the running system for failures or anomalies and
file an AgentObservation. The monitor's diagnose step uses Claude (plus the
company brain) to draft a MonitorDiagnosis containing a proposed fix as a
unified-diff patch. The owner approves each diagnosis with one tap; no patch
is ever applied automatically in this round.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class AgentObservation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agent_observations"
    __table_args__ = (
        Index("ix_agent_observations_status", "status"),
        Index(
            "ix_agent_observations_source",
            "source_type", "source_ref",
            unique=True,
        ),
    )

    # Observations may be tenant-wide (no company_id) — e.g. a worker exception.
    company_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True
    )
    # agent_task_failure | approval_rejection_cluster | metric_anomaly |
    # coo_action_failure | exception
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # low | medium | high
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    # new | analyzed | resolved | ignored
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new")

    diagnoses: Mapped[list[MonitorDiagnosis]] = relationship(
        "MonitorDiagnosis", back_populates="observation"
    )


class MonitorDiagnosis(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "monitor_diagnoses"
    __table_args__ = (
        Index("ix_monitor_diagnoses_status", "status"),
    )

    observation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agent_observations.id", ondelete="CASCADE"),
        nullable=False,
    )
    root_cause_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_fix: Mapped[str | None] = mapped_column(Text, nullable=True)
    # List of {"path": str, "patch": str}; concatenated unified-diff lives in proposed_fix.
    files_changed: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # low | medium | high
    confidence: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    # {"verdict": "approve"|"concerns"|"reject", "notes": str}
    reviewer_agent_verdict: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # proposed | approved | rejected | implemented
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="proposed")
    pr_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    pr_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    observation: Mapped[AgentObservation] = relationship(
        "AgentObservation", back_populates="diagnoses"
    )
