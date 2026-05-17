"""Automation roadmap: automation_items

Revision ID: 005_automation
Revises: 004_interview
Create Date: 2026-05-17
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "005_automation"
down_revision = "004_interview"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "automation_items",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "company_id", UUID(as_uuid=True),
            sa.ForeignKey("companies.id"), nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("category", sa.String(40)),
        sa.Column("source", sa.String(20), nullable=False, server_default="observed"),
        sa.Column("source_ref", sa.Text()),
        sa.Column("impact", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("effort", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("priority_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="proposed"),
        sa.Column("agent_task_id", UUID(as_uuid=True)),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("company_id", "title", name="uq_automation_company_title"),
    )


def downgrade() -> None:
    op.drop_table("automation_items")
