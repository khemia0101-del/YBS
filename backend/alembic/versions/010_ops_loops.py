"""Continuous ops loops: ops_loops, ops_loop_runs

Revision ID: 010_ops_loops
Revises: 009_monitor
Create Date: 2026-05-20
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "010_ops_loops"
down_revision = "009_monitor"
branch_labels = None
depends_on = None

_TS = sa.TIMESTAMP(timezone=True)
_NOW = sa.text("now()")
_PK = sa.text("gen_random_uuid()")


def upgrade() -> None:
    op.create_table(
        "ops_loops",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=_PK),
        sa.Column(
            "company_id", UUID(as_uuid=True),
            sa.ForeignKey("companies.id"), nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("focus", sa.String(20), nullable=False, server_default="metrics"),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column(
            "schedule_cron", sa.Text(), nullable=False, server_default="0 9 * * 1"
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("config", JSONB()),
        sa.Column("last_run_at", _TS),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
    )
    op.create_index(
        "ix_ops_loops_company_active", "ops_loops", ["company_id", "is_active"]
    )

    op.create_table(
        "ops_loop_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=_PK),
        sa.Column(
            "loop_id", UUID(as_uuid=True),
            sa.ForeignKey("ops_loops.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("started_at", _TS, nullable=False),
        sa.Column("ended_at", _TS),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("findings_summary", sa.Text()),
        sa.Column(
            "proposed_actions_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("error", sa.Text()),
    )
    op.create_index("ix_ops_loop_runs_loop", "ops_loop_runs", ["loop_id"])


def downgrade() -> None:
    op.drop_index("ix_ops_loop_runs_loop", table_name="ops_loop_runs")
    op.drop_table("ops_loop_runs")
    op.drop_index("ix_ops_loops_company_active", table_name="ops_loops")
    op.drop_table("ops_loops")
