from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    ARRAY,
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Tenant(Base, UUIDMixin, TimestampMixin):
    """A platform account. Owns one or more Companies (businesses)."""

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    companies: Mapped[list[Company]] = relationship("Company", back_populates="tenant")


class Company(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "companies"

    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    legal_name: Mapped[str] = mapped_column(Text, nullable=False)
    dba_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    ein: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    founded_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    acquisition_target: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="companies")
    customers: Mapped[list[Customer]] = relationship("Customer", back_populates="company")
    supervisors: Mapped[list[Supervisor]] = relationship("Supervisor", back_populates="company")
    subcontractors: Mapped[list[Subcontractor]] = relationship(
        "Subcontractor", back_populates="company"
    )


class Customer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "customers"

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    name_aliases: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    qb_customer_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="commercial"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    concentration_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4), nullable=True
    )

    # Relationships
    company: Mapped[Company] = relationship("Company", back_populates="customers")
    sites: Mapped[list[Site]] = relationship("Site", back_populates="customer")
    contracts: Mapped[list[Contract]] = relationship("Contract", back_populates="customer")


class Site(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "sites"

    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    site_name: Mapped[str] = mapped_column(Text, nullable=False)
    address: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    square_footage: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    swept_site_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    customer: Mapped[Customer] = relationship("Customer", back_populates="sites")
    contracts: Mapped[list[Contract]] = relationship("Contract", back_populates="site")


class Contract(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "contracts"

    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    site_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("sites.id"), nullable=True
    )
    contract_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    monthly_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    scope_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    service_frequency: Mapped[str | None] = mapped_column(Text, nullable=True)
    contract_type: Mapped[str] = mapped_column(String(20), nullable=False, default="fixed")
    auto_renews: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    renewal_notice_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    qb_class: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope_creep_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scope_creep_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evidence_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    calculation_version: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    customer: Mapped[Customer] = relationship("Customer", back_populates="contracts")
    site: Mapped[Site | None] = relationship("Site", back_populates="contracts")


class Supervisor(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "supervisors"

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    employee_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    sites_managed: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    company: Mapped[Company] = relationship("Company", back_populates="supervisors")


class Subcontractor(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "subcontractors"

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    contact_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    w9_on_file: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    payment_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    company: Mapped[Company] = relationship("Company", back_populates="subcontractors")


class ComplianceDocument(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "compliance_documents"

    entity_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    doc_type: Mapped[str] = mapped_column(Text, nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    s3_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
