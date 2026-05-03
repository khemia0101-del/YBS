from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.core import Company, Contract, Customer, Site


class Invoice(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "invoices"

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    contract_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=True
    )
    invoice_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    qb_invoice_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    line_items: Mapped[list | None] = mapped_column(JSON, nullable=True)
    days_outstanding: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    calculation_version: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    company: Mapped[Company] = relationship("Company")
    customer: Mapped[Customer] = relationship("Customer")
    contract: Mapped[Contract | None] = relationship("Contract")
    payments: Mapped[list[Payment]] = relationship("Payment", back_populates="invoice")


class Payment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "payments"

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    invoice_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True
    )
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    payment_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    bank_transaction_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    qb_payment_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unmatched")
    match_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    evidence_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    # Relationships
    company: Mapped[Company] = relationship("Company")
    customer: Mapped[Customer] = relationship("Customer")
    invoice: Mapped[Invoice | None] = relationship("Invoice", back_populates="payments")


class LaborShift(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "labor_shifts"

    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    site_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("sites.id"), nullable=True
    )
    contract_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=True
    )
    employee_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    employee_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    shift_date: Mapped[date] = mapped_column(Date, nullable=False)
    clock_in: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clock_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hours_worked: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    hourly_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    labor_cost: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    worker_type: Mapped[str] = mapped_column(String(5), nullable=False, default="W2")
    payroll_period: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_system: Mapped[str | None] = mapped_column(Text, nullable=True)
    swept_shift_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    calculation_version: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    company: Mapped[Company] = relationship("Company")
    site: Mapped[Site | None] = relationship("Site")
    contract: Mapped[Contract | None] = relationship("Contract")
