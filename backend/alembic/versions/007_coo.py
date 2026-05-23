"""AI COO: coo_conversations, coo_messages, coo_actions, employee_tasks, employee_messages

Revision ID: 007_coo
Revises: 006_profit
Create Date: 2026-05-17
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "007_coo"
down_revision = "006_profit"
branch_labels = None
depends_on = None

_TS = sa.TIMESTAMP(timezone=True)
_NOW = sa.text("now()")
_PK = sa.text("gen_random_uuid()")


def upgrade() -> None:
    op.create_table(
        "coo_conversations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=_PK),
        sa.Column(
            "company_id", UUID(as_uuid=True),
            sa.ForeignKey("companies.id"), nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False, server_default="New conversation"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
    )

    op.create_table(
        "coo_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=_PK),
        sa.Column(
            "conversation_id", UUID(as_uuid=True),
            sa.ForeignKey("coo_conversations.id"), nullable=False,
        ),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
    )
    op.create_index(
        "ix_coo_messages_conversation_seq", "coo_messages", ["conversation_id", "seq"]
    )

    op.create_table(
        "coo_actions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=_PK),
        sa.Column(
            "company_id", UUID(as_uuid=True),
            sa.ForeignKey("companies.id"), nullable=False,
        ),
        sa.Column(
            "conversation_id", UUID(as_uuid=True),
            sa.ForeignKey("coo_conversations.id"), nullable=True,
        ),
        sa.Column("action_type", sa.String(30), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("result", JSONB()),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
    )

    op.create_table(
        "employee_tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=_PK),
        sa.Column(
            "company_id", UUID(as_uuid=True),
            sa.ForeignKey("companies.id"), nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("assignee_name", sa.Text()),
        sa.Column("assignee_email", sa.Text()),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("source_action_id", UUID(as_uuid=True)),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
    )

    op.create_table(
        "employee_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=_PK),
        sa.Column(
            "company_id", UUID(as_uuid=True),
            sa.ForeignKey("companies.id"), nullable=False,
        ),
        sa.Column("to_email", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="sent"),
        sa.Column("source_action_id", UUID(as_uuid=True)),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
    )


def downgrade() -> None:
    op.drop_table("employee_messages")
    op.drop_table("employee_tasks")
    op.drop_table("coo_actions")
    op.drop_index("ix_coo_messages_conversation_seq", table_name="coo_messages")
    op.drop_table("coo_messages")
    op.drop_table("coo_conversations")
