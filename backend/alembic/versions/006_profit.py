"""Profitability recommendations: profit_recommendations

Revision ID: 006_profit
Revises: 005_automation
Create Date: 2026-05-17
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "006_profit"
down_revision = "005_automation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "profit_recommendations",
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
        sa.Column("category", sa.String(30), nullable=False, server_default="margin"),
        sa.Column("estimated_annual_impact", sa.Numeric(15, 2)),
        sa.Column("effort", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("confidence", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(20), nullable=False, server_default="proposed"),
        sa.Column("source", sa.String(20), nullable=False, server_default="rules"),
        sa.Column("rationale", sa.Text()),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "company_id", "title", name="uq_profit_rec_company_title"
        ),
    )


def downgrade() -> None:
    op.drop_table("profit_recommendations")
