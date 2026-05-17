"""Multi-tenancy: tenants table and tenant/company scoping

Revision ID: 002_multi_tenancy
Revises: 001_foundation
Create Date: 2026-05-17
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "002_multi_tenancy"
down_revision = "001_foundation"
branch_labels = None
depends_on = None

# Fixed id so pre-existing rows can be backfilled to a known tenant.
LEGACY_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.execute(
        "INSERT INTO tenants (id, name, slug, is_active) "
        f"VALUES ('{LEGACY_TENANT_ID}', 'Legacy Tenant', 'legacy', true)"
    )

    # companies.tenant_id — required; backfill existing rows to the legacy tenant.
    op.add_column("companies", sa.Column("tenant_id", UUID(as_uuid=True), nullable=True))
    op.execute(
        f"UPDATE companies SET tenant_id = '{LEGACY_TENANT_ID}' WHERE tenant_id IS NULL"
    )
    op.alter_column("companies", "tenant_id", nullable=False)
    op.create_foreign_key(
        "companies_tenant_id_fkey", "companies", "tenants", ["tenant_id"], ["id"]
    )

    # users.tenant_id — nullable (a user without a tenant has no data access).
    op.add_column("users", sa.Column("tenant_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "users_tenant_id_fkey", "users", "tenants", ["tenant_id"], ["id"]
    )

    # Ingestion tables get a company scope.
    for table in ("raw_records", "staged_records", "sync_logs"):
        op.add_column(table, sa.Column("company_id", UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            f"{table}_company_id_fkey", table, "companies", ["company_id"], ["id"]
        )


def downgrade() -> None:
    for table in ("sync_logs", "staged_records", "raw_records"):
        op.drop_constraint(f"{table}_company_id_fkey", table, type_="foreignkey")
        op.drop_column(table, "company_id")
    op.drop_constraint("users_tenant_id_fkey", "users", type_="foreignkey")
    op.drop_column("users", "tenant_id")
    op.drop_constraint("companies_tenant_id_fkey", "companies", type_="foreignkey")
    op.drop_column("companies", "tenant_id")
    op.drop_table("tenants")
