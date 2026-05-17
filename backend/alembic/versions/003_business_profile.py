"""Adaptive business profile: business_profiles, metric_definitions, metric_snapshots

Revision ID: 003_business_profile
Revises: 002_multi_tenancy
Create Date: 2026-05-17
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "003_business_profile"
down_revision = "002_multi_tenancy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "business_profiles",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "company_id", UUID(as_uuid=True),
            sa.ForeignKey("companies.id"), nullable=False,
        ),
        sa.Column("industry", sa.Text()),
        sa.Column("business_model", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("north_star_metric", sa.Text()),
        sa.Column("growth_goal", JSONB()),
        sa.Column("automation_candidates", JSONB()),
        sa.Column("config", JSONB()),
        sa.Column("source", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("is_confirmed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("company_id", name="uq_business_profile_company"),
    )

    op.create_table(
        "metric_definitions",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "company_id", UUID(as_uuid=True),
            sa.ForeignKey("companies.id"), nullable=False,
        ),
        sa.Column(
            "profile_id", UUID(as_uuid=True),
            sa.ForeignKey("business_profiles.id"), nullable=True,
        ),
        sa.Column("key", sa.String(60), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("unit", sa.String(20), nullable=False, server_default="count"),
        sa.Column("category", sa.String(30)),
        sa.Column("source", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("formula", sa.Text()),
        sa.Column("target_value", sa.Numeric(18, 4)),
        sa.Column("is_north_star", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("company_id", "key", name="uq_metric_def_company_key"),
    )

    op.create_table(
        "metric_snapshots",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "company_id", UUID(as_uuid=True),
            sa.ForeignKey("companies.id"), nullable=False,
        ),
        sa.Column(
            "metric_definition_id", UUID(as_uuid=True),
            sa.ForeignKey("metric_definitions.id"), nullable=False,
        ),
        sa.Column("period_date", sa.Date(), nullable=False),
        sa.Column("period_type", sa.String(20), nullable=False, server_default="monthly"),
        sa.Column("value", sa.Numeric(18, 4), nullable=False),
        sa.Column("source", sa.String(20), nullable=False, server_default="computed"),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_metric_snapshots_def_date",
        "metric_snapshots",
        ["metric_definition_id", "period_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_metric_snapshots_def_date", table_name="metric_snapshots")
    op.drop_table("metric_snapshots")
    op.drop_table("metric_definitions")
    op.drop_table("business_profiles")
