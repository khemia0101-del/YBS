"""Self-improving monitor: agent_observations, monitor_diagnoses

Revision ID: 009_monitor
Revises: 008_knowledge
Create Date: 2026-05-20
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "009_monitor"
down_revision = "008_knowledge"
branch_labels = None
depends_on = None

_TS = sa.TIMESTAMP(timezone=True)
_NOW = sa.text("now()")
_PK = sa.text("gen_random_uuid()")


def upgrade() -> None:
    op.create_table(
        "agent_observations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=_PK),
        sa.Column(
            "company_id", UUID(as_uuid=True),
            sa.ForeignKey("companies.id"), nullable=True,
        ),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", JSONB()),
        sa.Column("severity", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(20), nullable=False, server_default="new"),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
    )
    op.create_index(
        "ix_agent_observations_status", "agent_observations", ["status"]
    )
    op.create_index(
        "ix_agent_observations_source",
        "agent_observations",
        ["source_type", "source_ref"],
        unique=True,
    )

    op.create_table(
        "monitor_diagnoses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=_PK),
        sa.Column(
            "observation_id", UUID(as_uuid=True),
            sa.ForeignKey("agent_observations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("root_cause_summary", sa.Text()),
        sa.Column("proposed_fix", sa.Text()),
        sa.Column("files_changed", JSONB()),
        sa.Column("confidence", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("reviewer_agent_verdict", JSONB()),
        sa.Column("status", sa.String(20), nullable=False, server_default="proposed"),
        sa.Column("pr_url", sa.Text()),
        sa.Column("pr_description", sa.Text()),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
    )
    op.create_index(
        "ix_monitor_diagnoses_status", "monitor_diagnoses", ["status"]
    )


def downgrade() -> None:
    op.drop_index("ix_monitor_diagnoses_status", table_name="monitor_diagnoses")
    op.drop_table("monitor_diagnoses")
    op.drop_index("ix_agent_observations_source", table_name="agent_observations")
    op.drop_index("ix_agent_observations_status", table_name="agent_observations")
    op.drop_table("agent_observations")
