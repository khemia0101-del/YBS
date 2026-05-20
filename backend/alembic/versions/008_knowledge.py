"""Company brain: knowledge_documents, knowledge_chunks

Revision ID: 008_knowledge
Revises: 007_coo
Create Date: 2026-05-20
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "008_knowledge"
down_revision = "007_coo"
branch_labels = None
depends_on = None

_TS = sa.TIMESTAMP(timezone=True)
_NOW = sa.text("now()")
_PK = sa.text("gen_random_uuid()")


def upgrade() -> None:
    op.create_table(
        "knowledge_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=_PK),
        sa.Column(
            "company_id", UUID(as_uuid=True),
            sa.ForeignKey("companies.id"), nullable=False,
        ),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("source_ref", sa.Text()),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("meta", JSONB()),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
    )
    op.create_index(
        "ix_knowledge_documents_company_source",
        "knowledge_documents",
        ["company_id", "source_type"],
    )
    op.create_index(
        "ix_knowledge_documents_source_ref",
        "knowledge_documents",
        ["company_id", "source_type", "source_ref"],
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=_PK),
        sa.Column(
            "document_id", UUID(as_uuid=True),
            sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "company_id", UUID(as_uuid=True),
            sa.ForeignKey("companies.id"), nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", JSONB()),
        sa.Column("token_count", sa.Integer()),
    )
    op.create_index(
        "ix_knowledge_chunks_document", "knowledge_chunks", ["document_id"]
    )
    op.create_index(
        "ix_knowledge_chunks_company", "knowledge_chunks", ["company_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_company", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_document", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.drop_index(
        "ix_knowledge_documents_source_ref", table_name="knowledge_documents"
    )
    op.drop_index(
        "ix_knowledge_documents_company_source", table_name="knowledge_documents"
    )
    op.drop_table("knowledge_documents")
