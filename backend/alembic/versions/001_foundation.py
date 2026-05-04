"""Foundation schema: all core tables

Revision ID: 001_foundation
Revises:
Create Date: 2026-05-03
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

revision = "001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("hashed_password", sa.Text(), nullable=False),
        sa.Column("full_name", sa.Text()),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_login_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("role IN ('admin','analyst','operator','viewer','agent')", name="users_role_check"),
    )

    # ── Audit Logs (immutable — application enforces append-only) ─────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("actor_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("actor_type", sa.Text(), nullable=False),
        sa.Column("table_name", sa.Text()),
        sa.Column("record_id", UUID(as_uuid=True)),
        sa.Column("before_state", JSONB()),
        sa.Column("after_state", JSONB()),
        sa.Column("metadata", JSONB()),
        sa.Column("ip_address", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("actor_type IN ('user','agent','system')", name="audit_logs_actor_type_check"),
    )
    op.create_index("idx_audit_logs_record", "audit_logs", ["table_name", "record_id"])
    op.create_index("idx_audit_logs_actor", "audit_logs", ["actor_id", sa.text("created_at DESC")])

    # ── Raw Records (immutable once written) ──────────────────────────────────
    op.create_table(
        "raw_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_system", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text()),
        sa.Column("raw_payload", JSONB(), nullable=False),
        sa.Column("file_s3_key", sa.Text()),
        sa.Column("checksum", sa.Text(), nullable=False),
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("ingested_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("is_duplicate", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("duplicate_of", UUID(as_uuid=True), sa.ForeignKey("raw_records.id", ondelete="SET NULL")),
        sa.CheckConstraint(
            "source_system IN ('quickbooks','bank_csv','payroll','swept','email','manual')",
            name="raw_records_source_system_check",
        ),
    )
    op.create_index("idx_raw_records_source", "raw_records", ["source_system", "source_ref"])
    op.create_index("idx_raw_records_ingested", "raw_records", [sa.text("ingested_at DESC")])
    op.create_index(
        "idx_raw_records_checksum_unique",
        "raw_records",
        ["checksum"],
        unique=True,
        postgresql_where=sa.text("is_duplicate = false"),
    )

    # ── Staged Records ────────────────────────────────────────────────────────
    op.create_table(
        "staged_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("raw_record_id", UUID(as_uuid=True), sa.ForeignKey("raw_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("record_type", sa.Text(), nullable=False),
        sa.Column("extracted_data", JSONB(), nullable=False),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("confidence_reasons", JSONB()),
        sa.Column("match_suggestions", JSONB()),
        sa.Column("status", sa.Text(), nullable=False, server_default="'pending'"),
        sa.Column("reviewed_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("review_notes", sa.Text()),
        sa.Column("auto_approved_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("auto_approval_rule", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "record_type IN ('customer','contract','site','invoice','payment','labor_shift','subcontractor')",
            name="staged_records_record_type_check",
        ),
        sa.CheckConstraint(
            "status IN ('pending','approved','rejected','needs_review','auto_approved')",
            name="staged_records_status_check",
        ),
        sa.CheckConstraint("confidence_score BETWEEN 0 AND 1", name="staged_records_confidence_check"),
    )
    op.create_index("idx_staged_status", "staged_records", ["status", sa.text("created_at DESC")])
    op.create_index("idx_staged_raw", "staged_records", ["raw_record_id"])
    op.create_index("idx_staged_type_status", "staged_records", ["record_type", "status"])

    # ── Companies ─────────────────────────────────────────────────────────────
    op.create_table(
        "companies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("legal_name", sa.Text(), nullable=False),
        sa.Column("dba_name", sa.Text()),
        sa.Column("ein", sa.Text()),
        sa.Column("address", JSONB()),
        sa.Column("founded_date", sa.Date()),
        sa.Column("acquisition_target", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── Customers ─────────────────────────────────────────────────────────────
    op.create_table(
        "customers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("name_aliases", ARRAY(sa.Text())),
        sa.Column("qb_customer_id", sa.Text()),
        sa.Column("industry", sa.Text()),
        sa.Column("customer_type", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("concentration_pct", sa.Numeric(6, 4)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "customer_type IN ('commercial','government','nonprofit') OR customer_type IS NULL",
            name="customers_type_check",
        ),
    )
    op.create_index("idx_customers_company", "customers", ["company_id"])
    op.create_index("idx_customers_qb", "customers", ["qb_customer_id"])

    # ── Sites ─────────────────────────────────────────────────────────────────
    op.create_table(
        "sites",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("site_name", sa.Text(), nullable=False),
        sa.Column("address", JSONB()),
        sa.Column("square_footage", sa.Numeric(12, 2)),
        sa.Column("swept_site_id", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_sites_customer", "sites", ["customer_id"])

    # ── Contracts ─────────────────────────────────────────────────────────────
    op.create_table(
        "contracts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("site_id", UUID(as_uuid=True), sa.ForeignKey("sites.id", ondelete="SET NULL")),
        sa.Column("contract_number", sa.Text()),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date()),
        sa.Column("monthly_value", sa.Numeric(15, 2), nullable=False),
        sa.Column("scope_description", sa.Text()),
        sa.Column("service_frequency", sa.Text()),
        sa.Column("contract_type", sa.Text()),
        sa.Column("auto_renews", sa.Boolean(), server_default="false"),
        sa.Column("renewal_notice_days", sa.Integer()),
        sa.Column("status", sa.Text(), nullable=False, server_default="'active'"),
        sa.Column("qb_class", sa.Text()),
        sa.Column("scope_creep_flag", sa.Boolean(), server_default="false"),
        sa.Column("scope_creep_details", JSONB()),
        sa.Column("evidence_id", UUID(as_uuid=True)),
        sa.Column("confidence_score", sa.Numeric(5, 4)),
        sa.Column("calculation_version", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "status IN ('active','expired','terminated','pending','suspended')",
            name="contracts_status_check",
        ),
        sa.CheckConstraint(
            "contract_type IN ('fixed','variable','t_and_m') OR contract_type IS NULL",
            name="contracts_type_check",
        ),
    )
    op.create_index("idx_contracts_customer", "contracts", ["customer_id"])
    op.create_index("idx_contracts_status", "contracts", ["status"])

    # ── Supervisors ───────────────────────────────────────────────────────────
    op.create_table(
        "supervisors",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("employee_id", sa.Text()),
        sa.Column("sites_managed", ARRAY(UUID(as_uuid=True))),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── Subcontractors ────────────────────────────────────────────────────────
    op.create_table(
        "subcontractors",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("contact_info", JSONB()),
        sa.Column("w9_on_file", sa.Boolean(), server_default="false"),
        sa.Column("payment_terms", sa.Text()),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── Compliance Documents ──────────────────────────────────────────────────
    op.create_table(
        "compliance_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("doc_type", sa.Text(), nullable=False),
        sa.Column("expiry_date", sa.Date()),
        sa.Column("s3_key", sa.Text()),
        sa.Column("status", sa.Text(), server_default="'active'"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── Invoices ──────────────────────────────────────────────────────────────
    op.create_table(
        "invoices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contract_id", UUID(as_uuid=True), sa.ForeignKey("contracts.id", ondelete="SET NULL")),
        sa.Column("invoice_number", sa.Text(), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date()),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("amount_paid", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.Text(), nullable=False, server_default="'open'"),
        sa.Column("qb_invoice_id", sa.Text()),
        sa.Column("line_items", JSONB()),
        sa.Column("days_outstanding", sa.Integer()),
        sa.Column("evidence_id", UUID(as_uuid=True)),
        sa.Column("confidence_score", sa.Numeric(5, 4)),
        sa.Column("calculation_version", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "status IN ('draft','open','partial','paid','overdue','void','disputed')",
            name="invoices_status_check",
        ),
    )
    op.create_index("idx_invoices_customer", "invoices", ["customer_id"])
    op.create_index("idx_invoices_status", "invoices", ["status", "due_date"])
    op.create_index("idx_invoices_qb", "invoices", ["qb_invoice_id"])

    # ── Payments ──────────────────────────────────────────────────────────────
    op.create_table(
        "payments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="SET NULL")),
        sa.Column("invoice_id", UUID(as_uuid=True), sa.ForeignKey("invoices.id", ondelete="SET NULL")),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("payment_method", sa.Text()),
        sa.Column("reference_number", sa.Text()),
        sa.Column("bank_transaction_id", sa.Text()),
        sa.Column("qb_payment_id", sa.Text()),
        sa.Column("match_status", sa.Text(), nullable=False, server_default="'unmatched'"),
        sa.Column("match_confidence", sa.Numeric(5, 4)),
        sa.Column("evidence_id", UUID(as_uuid=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "match_status IN ('matched','unmatched','partial','disputed')",
            name="payments_match_status_check",
        ),
    )
    op.create_index("idx_payments_invoice", "payments", ["invoice_id"])
    op.create_index("idx_payments_customer", "payments", ["customer_id"])
    op.create_index("idx_payments_date", "payments", [sa.text("payment_date DESC")])

    # ── Labor Shifts ──────────────────────────────────────────────────────────
    op.create_table(
        "labor_shifts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("site_id", UUID(as_uuid=True), sa.ForeignKey("sites.id", ondelete="SET NULL")),
        sa.Column("contract_id", UUID(as_uuid=True), sa.ForeignKey("contracts.id", ondelete="SET NULL")),
        sa.Column("employee_id", sa.Text()),
        sa.Column("employee_name", sa.Text()),
        sa.Column("shift_date", sa.Date(), nullable=False),
        sa.Column("clock_in", sa.TIMESTAMP(timezone=True)),
        sa.Column("clock_out", sa.TIMESTAMP(timezone=True)),
        sa.Column("hours_worked", sa.Numeric(6, 2)),
        sa.Column("hourly_rate", sa.Numeric(10, 2)),
        sa.Column("labor_cost", sa.Numeric(15, 2)),
        sa.Column("worker_type", sa.Text(), nullable=False, server_default="'W2'"),
        sa.Column("payroll_period", sa.Text()),
        sa.Column("source_system", sa.Text()),
        sa.Column("swept_shift_id", sa.Text()),
        sa.Column("evidence_id", UUID(as_uuid=True)),
        sa.Column("confidence_score", sa.Numeric(5, 4)),
        sa.Column("calculation_version", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("worker_type IN ('W2','SUB')", name="labor_shifts_worker_type_check"),
    )
    op.create_index("idx_labor_site", "labor_shifts", ["site_id", sa.text("shift_date DESC")])
    op.create_index("idx_labor_contract", "labor_shifts", ["contract_id"])

    # ── Sync Logs ─────────────────────────────────────────────────────────────
    op.create_table(
        "sync_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_system", sa.Text(), nullable=False),
        sa.Column("realm_id", sa.Text()),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("records_ingested", sa.Integer(), server_default="0"),
        sa.Column("errors_json", JSONB()),
        sa.Column("status", sa.Text(), server_default="'running'"),
    )

    # ── Integration Credentials ───────────────────────────────────────────────
    op.create_table(
        "integration_credentials",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_system", sa.Text(), nullable=False),
        sa.Column("credential_type", sa.Text(), nullable=False),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("metadata_json", JSONB()),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── Labor Burden Assumptions ──────────────────────────────────────────────
    op.create_table(
        "labor_burden_assumptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE")),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("fica_employer_pct", sa.Numeric(8, 6), nullable=False, server_default="0.0765"),
        sa.Column("futa_pct", sa.Numeric(8, 6), nullable=False, server_default="0.006"),
        sa.Column("suta_pct", sa.Numeric(8, 6), nullable=False, server_default="0.027"),
        sa.Column("workers_comp_pct", sa.Numeric(8, 6), nullable=False, server_default="0.035"),
        sa.Column("benefits_pct", sa.Numeric(8, 6), nullable=False, server_default="0"),
        sa.Column("training_pct", sa.Numeric(8, 6), nullable=False, server_default="0.005"),
        sa.Column("total_burden_pct", sa.Numeric(8, 6), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("effective_date", sa.Date()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── Profitability Runs ────────────────────────────────────────────────────
    op.create_table(
        "profitability_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("calculation_version", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="'draft'"),
        sa.Column("approved_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("approved_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("total_revenue", sa.Numeric(15, 2)),
        sa.Column("total_direct_labor", sa.Numeric(15, 2)),
        sa.Column("total_subcontractor", sa.Numeric(15, 2)),
        sa.Column("total_supplies", sa.Numeric(15, 2)),
        sa.Column("total_overhead_alloc", sa.Numeric(15, 2)),
        sa.Column("gross_profit", sa.Numeric(15, 2)),
        sa.Column("gross_margin_pct", sa.Numeric(8, 6)),
        sa.Column("ebitda", sa.Numeric(15, 2)),
        sa.Column("ebitda_margin_pct", sa.Numeric(8, 6)),
        sa.Column("evidence_bundle", JSONB()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("status IN ('draft','approved','superseded')", name="profitability_runs_status_check"),
    )

    # ── Profitability Run Lines ───────────────────────────────────────────────
    op.create_table(
        "profitability_run_lines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("profitability_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contract_id", UUID(as_uuid=True), sa.ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revenue", sa.Numeric(15, 2)),
        sa.Column("direct_labor_cost", sa.Numeric(15, 2)),
        sa.Column("labor_burden_pct", sa.Numeric(8, 6)),
        sa.Column("burdened_labor_cost", sa.Numeric(15, 2)),
        sa.Column("subcontractor_cost", sa.Numeric(15, 2)),
        sa.Column("supplies_cost", sa.Numeric(15, 2)),
        sa.Column("overhead_alloc", sa.Numeric(15, 2)),
        sa.Column("contribution_margin", sa.Numeric(15, 2)),
        sa.Column("contribution_margin_pct", sa.Numeric(8, 6)),
        sa.Column("gross_profit", sa.Numeric(15, 2)),
        sa.Column("gross_margin_pct", sa.Numeric(8, 6)),
        sa.Column("scope_creep_adj", sa.Numeric(15, 2)),
        sa.Column("evidence_id", UUID(as_uuid=True)),
        sa.Column("confidence_score", sa.Numeric(5, 4)),
        sa.Column("calculation_version", sa.Text()),
    )
    op.create_index("idx_prof_lines_run", "profitability_run_lines", ["run_id"])
    op.create_index("idx_prof_lines_contract", "profitability_run_lines", ["contract_id"])

    # ── DSO Snapshots ─────────────────────────────────────────────────────────
    op.create_table(
        "dso_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("dso_days", sa.Numeric(8, 2)),
        sa.Column("total_ar", sa.Numeric(15, 2)),
        sa.Column("avg_daily_revenue", sa.Numeric(15, 2)),
        sa.Column("aging_0_30", sa.Numeric(15, 2)),
        sa.Column("aging_31_60", sa.Numeric(15, 2)),
        sa.Column("aging_61_90", sa.Numeric(15, 2)),
        sa.Column("aging_91_plus", sa.Numeric(15, 2)),
        sa.Column("evidence_id", UUID(as_uuid=True)),
        sa.Column("calculation_version", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── Cash Forecast Runs ────────────────────────────────────────────────────
    op.create_table(
        "cash_forecast_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column("forecast_start", sa.Date(), nullable=False),
        sa.Column("forecast_weeks", sa.Integer(), nullable=False, server_default="13"),
        sa.Column("mode", sa.Text(), nullable=False, server_default="'baseline'"),
        sa.Column("beginning_cash", sa.Numeric(15, 2)),
        sa.Column("ending_cash", sa.Numeric(15, 2)),
        sa.Column("min_cash_week", sa.Integer()),
        sa.Column("min_cash_amount", sa.Numeric(15, 2)),
        sa.Column("payroll_covered_through", sa.Date()),
        sa.Column("status", sa.Text(), server_default="'draft'"),
        sa.Column("approved_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("mode IN ('baseline','optimistic','stress')", name="cash_forecast_mode_check"),
    )

    # ── Cash Forecast Weeks ───────────────────────────────────────────────────
    op.create_table(
        "cash_forecast_weeks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("cash_forecast_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("week_number", sa.Integer(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("beginning_cash", sa.Numeric(15, 2)),
        sa.Column("ar_collections", sa.Numeric(15, 2)),
        sa.Column("other_inflows", sa.Numeric(15, 2)),
        sa.Column("payroll_outflow", sa.Numeric(15, 2)),
        sa.Column("subcontractor_outflow", sa.Numeric(15, 2)),
        sa.Column("overhead_outflow", sa.Numeric(15, 2)),
        sa.Column("other_outflows", sa.Numeric(15, 2)),
        sa.Column("net_cash_flow", sa.Numeric(15, 2)),
        sa.Column("ending_cash", sa.Numeric(15, 2)),
        sa.Column("notes", sa.Text()),
    )

    # ── Stress Test Runs ──────────────────────────────────────────────────────
    op.create_table(
        "stress_test_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("base_forecast_id", UUID(as_uuid=True), sa.ForeignKey("cash_forecast_runs.id", ondelete="SET NULL")),
        sa.Column("scenario_name", sa.Text(), nullable=False),
        sa.Column("scenario_params", JSONB(), nullable=False),
        sa.Column("result_summary", JSONB()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── Decisions ─────────────────────────────────────────────────────────────
    op.create_table(
        "decisions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_type", sa.Text(), nullable=False),
        sa.Column("subject_id", UUID(as_uuid=True), nullable=False),
        sa.Column("decision_type", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("rationale", JSONB(), nullable=False),
        sa.Column("recommended_action", sa.Text()),
        sa.Column("recommended_price", sa.Numeric(15, 2)),
        sa.Column("status", sa.Text(), nullable=False, server_default="'pending'"),
        sa.Column("approved_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("approved_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("executed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("calculation_version", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "subject_type IN ('contract','customer','bid','site')",
            name="decisions_subject_type_check",
        ),
        sa.CheckConstraint(
            "decision_type IN ('bid','no_bid','reprice','renegotiate','terminate','monitor')",
            name="decisions_type_check",
        ),
        sa.CheckConstraint(
            "label IN ('AUTO','APPROVAL_REQUIRED','BLOCKED')",
            name="decisions_label_check",
        ),
        sa.CheckConstraint(
            "status IN ('pending','approved','rejected','executed')",
            name="decisions_status_check",
        ),
    )

    # ── Manual Overrides ──────────────────────────────────────────────────────
    op.create_table(
        "manual_overrides",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("table_name", sa.Text(), nullable=False),
        sa.Column("record_id", UUID(as_uuid=True), nullable=False),
        sa.Column("field_name", sa.Text(), nullable=False),
        sa.Column("original_value", JSONB()),
        sa.Column("override_value", JSONB(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("overridden_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── Prediction Tracking ───────────────────────────────────────────────────
    op.create_table(
        "prediction_tracking",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("prediction_type", sa.Text(), nullable=False),
        sa.Column("subject_id", UUID(as_uuid=True)),
        sa.Column("predicted_value", JSONB()),
        sa.Column("actual_value", JSONB()),
        sa.Column("accuracy_score", sa.Numeric(5, 4)),
        sa.Column("evaluated_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── QoE Runs ──────────────────────────────────────────────────────────────
    op.create_table(
        "qoe_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column("analysis_period_start", sa.Date(), nullable=False),
        sa.Column("analysis_period_end", sa.Date(), nullable=False),
        sa.Column("reported_ebitda", sa.Numeric(15, 2)),
        sa.Column("adjusted_ebitda", sa.Numeric(15, 2)),
        sa.Column("total_addbacks", sa.Numeric(15, 2)),
        sa.Column("total_negative_adj", sa.Numeric(15, 2)),
        sa.Column("normalized_ebitda", sa.Numeric(15, 2)),
        sa.Column("ebitda_margin_pct", sa.Numeric(8, 6)),
        sa.Column("revenue_concentration_flag", sa.Boolean()),
        sa.Column("customer_count", sa.Integer()),
        sa.Column("calculation_version", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="'draft'"),
        sa.Column("approved_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("approved_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("evidence_bundle", JSONB()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── ESOP Adjustments ──────────────────────────────────────────────────────
    op.create_table(
        "esop_adjustments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("qoe_run_id", UUID(as_uuid=True), sa.ForeignKey("qoe_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("adj_type", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("period", sa.Text()),
        sa.Column("evidence_id", UUID(as_uuid=True)),
        sa.Column("evidence_description", sa.Text()),
        sa.Column("confidence_score", sa.Numeric(5, 4)),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("approved_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("approved_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "adj_type IN ('addback','negative','reclassification','normalization')",
            name="esop_adj_type_check",
        ),
    )

    # ── Valuation Evidence Files ──────────────────────────────────────────────
    op.create_table(
        "valuation_evidence_files",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("qoe_run_id", UUID(as_uuid=True), sa.ForeignKey("qoe_runs.id", ondelete="SET NULL")),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("file_s3_key", sa.Text(), nullable=False),
        sa.Column("file_type", sa.Text()),
        sa.Column("category", sa.Text()),
        sa.Column("period_covered", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("uploaded_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── Agent Tasks ───────────────────────────────────────────────────────────
    op.create_table(
        "agent_tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_type", sa.Text(), nullable=False),
        sa.Column("subject_type", sa.Text()),
        sa.Column("subject_id", UUID(as_uuid=True)),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("status", sa.Text(), nullable=False, server_default="'queued'"),
        sa.Column("agent_id", sa.Text()),
        sa.Column("input_params", JSONB()),
        sa.Column("output_data", JSONB()),
        sa.Column("error_message", sa.Text()),
        sa.Column("retry_count", sa.Integer(), server_default="0"),
        sa.Column("max_retries", sa.Integer(), server_default="3"),
        sa.Column("scheduled_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("parent_task_id", UUID(as_uuid=True), sa.ForeignKey("agent_tasks.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("priority BETWEEN 1 AND 10", name="agent_tasks_priority_check"),
        sa.CheckConstraint(
            "status IN ('queued','running','awaiting_approval','approved','rejected','completed','failed','terminal_failed')",
            name="agent_tasks_status_check",
        ),
    )
    op.create_index("idx_agent_tasks_status", "agent_tasks", ["status", sa.text("priority DESC")])
    op.create_index("idx_agent_tasks_company", "agent_tasks", ["company_id", "status"])

    # ── Agent Action Logs (immutable — append only) ───────────────────────────
    op.create_table(
        "agent_action_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("task_id", UUID(as_uuid=True), sa.ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", sa.Text(), nullable=False),
        sa.Column("action_type", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("input_snapshot", JSONB()),
        sa.Column("output_snapshot", JSONB()),
        sa.Column("tables_read", ARRAY(sa.Text())),
        sa.Column("tables_written", ARRAY(sa.Text())),
        sa.Column("was_approved", sa.Boolean()),
        sa.Column("approved_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── Approval Requests ─────────────────────────────────────────────────────
    op.create_table(
        "approval_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", UUID(as_uuid=True), sa.ForeignKey("agent_tasks.id", ondelete="SET NULL")),
        sa.Column("decision_id", UUID(as_uuid=True), sa.ForeignKey("decisions.id", ondelete="SET NULL")),
        sa.Column("requested_by", sa.Text(), nullable=False),
        sa.Column("subject_description", sa.Text(), nullable=False),
        sa.Column("action_description", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.Text(), nullable=False),
        sa.Column("required_role", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="'pending'"),
        sa.Column("reviewed_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("review_notes", sa.Text()),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "risk_level IN ('low','medium','high','critical')",
            name="approval_requests_risk_level_check",
        ),
        sa.CheckConstraint(
            "status IN ('pending','approved','rejected','expired')",
            name="approval_requests_status_check",
        ),
    )
    op.create_index("idx_approval_status", "approval_requests", ["status", "risk_level", sa.text("created_at DESC")])

    # ── Communication Templates ───────────────────────────────────────────────
    op.create_table(
        "communication_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE")),
        sa.Column("template_name", sa.Text(), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("subject_template", sa.Text()),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("variables", JSONB()),
        sa.Column("use_case", sa.Text()),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("channel IN ('email','telegram','sms')", name="comm_templates_channel_check"),
    )

    # ── Rule Change Proposals ─────────────────────────────────────────────────
    op.create_table(
        "rule_change_proposals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("proposed_by", sa.Text(), nullable=False),
        sa.Column("rule_type", sa.Text(), nullable=False),
        sa.Column("current_value", JSONB()),
        sa.Column("proposed_value", JSONB(), nullable=False),
        sa.Column("rationale", sa.Text()),
        sa.Column("status", sa.Text(), server_default="'pending'"),
        sa.Column("reviewed_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── Agent Memory Exports ──────────────────────────────────────────────────
    op.create_table(
        "agent_memory_exports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agent_id", sa.Text(), nullable=False),
        sa.Column("export_type", sa.Text(), nullable=False),
        sa.Column("memory_snapshot", JSONB(), nullable=False),
        sa.Column("exported_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    tables_in_order = [
        "agent_memory_exports", "rule_change_proposals", "communication_templates",
        "approval_requests", "agent_action_logs", "agent_tasks",
        "valuation_evidence_files", "esop_adjustments", "qoe_runs",
        "prediction_tracking", "manual_overrides", "decisions",
        "stress_test_runs", "cash_forecast_weeks", "cash_forecast_runs",
        "dso_snapshots", "profitability_run_lines", "profitability_runs",
        "labor_burden_assumptions", "integration_credentials", "sync_logs",
        "labor_shifts", "payments", "invoices",
        "compliance_documents", "subcontractors", "supervisors",
        "contracts", "sites", "customers", "companies",
        "staged_records", "raw_records", "audit_logs", "users",
    ]
    for table in tables_in_order:
        op.drop_table(table)
