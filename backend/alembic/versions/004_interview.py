"""AI interview: interview_sessions, interview_messages, interview_insights

Revision ID: 004_interview
Revises: 003_business_profile
Create Date: 2026-05-17
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "004_interview"
down_revision = "003_business_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "interview_sessions",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "company_id", UUID(as_uuid=True),
            sa.ForeignKey("companies.id"), nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("interviewee_name", sa.Text()),
        sa.Column("interviewee_email", sa.Text()),
        sa.Column("purpose", sa.String(20), nullable=False, server_default="operations"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "interview_messages",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "session_id", UUID(as_uuid=True),
            sa.ForeignKey("interview_sessions.id"), nullable=False,
        ),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("sender", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_interview_messages_session_seq",
        "interview_messages",
        ["session_id", "seq"],
    )

    op.create_table(
        "interview_insights",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "session_id", UUID(as_uuid=True),
            sa.ForeignKey("interview_sessions.id"), nullable=False,
        ),
        sa.Column(
            "company_id", UUID(as_uuid=True),
            sa.ForeignKey("companies.id"), nullable=False,
        ),
        sa.Column("insight_type", sa.String(40), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", JSONB()),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("interview_insights")
    op.drop_index(
        "ix_interview_messages_session_seq", table_name="interview_messages"
    )
    op.drop_table("interview_messages")
    op.drop_table("interview_sessions")
