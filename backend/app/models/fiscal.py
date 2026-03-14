"""VULKRAN OS — Fiscal & tax models for Spanish tax system."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import String, Text, Integer, Numeric, Date, ForeignKey, DateTime, Boolean, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, new_uuid


class FiscalConfig(Base, TimestampMixin):
    """Tax configuration per client (regime, rates, IAE code)."""

    __tablename__ = "fiscal_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid,
        server_default=text("gen_random_uuid()"),
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), unique=True, nullable=False,
    )
    tax_regime: Mapped[str] = mapped_column(
        String(30), nullable=False, default="autonomo",
    )
    # autonomo | sl | slp | cooperativa
    vat_registered: Mapped[bool] = mapped_column(Boolean, default=True)
    irpf_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("15.00"))
    # 15% standard, 7% new autonomos (first 3 years)
    activity_code: Mapped[str | None] = mapped_column(String(20))
    # IAE code (e.g. 844 for marketing agencies)
    fiscal_name: Mapped[str | None] = mapped_column(String(200))
    nif: Mapped[str | None] = mapped_column(String(20))
    fiscal_address: Mapped[str | None] = mapped_column(Text)
    bank_iban: Mapped[str | None] = mapped_column(String(34))


class TaxObligation(Base, TimestampMixin):
    """Track tax filing obligations (Modelo 303, 130, 390, Renta)."""

    __tablename__ = "tax_obligations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid,
        server_default=text("gen_random_uuid()"),
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True,
    )
    obligation_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
    )
    # modelo_303 | modelo_130 | modelo_390 | modelo_349 | renta
    period: Mapped[str] = mapped_column(String(10), nullable=False)
    # Q1, Q2, Q3, Q4 (quarters) or ANNUAL
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    quarter: Mapped[int | None] = mapped_column(Integer)
    # 1-4 for quarterly, null for annual
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending",
    )
    # pending | calculated | filed | paid
    amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    # Amount to pay (positive) or refund (negative)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    filed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    calculation_data: Mapped[dict | None] = mapped_column(JSONB)
    # Detailed breakdown of the calculation
    notes: Mapped[str | None] = mapped_column(Text)


class RecurringInvoice(Base, TimestampMixin):
    """Template for auto-generated recurring invoices."""

    __tablename__ = "recurring_invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid,
        server_default=text("gen_random_uuid()"),
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True,
    )
    template_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # {items: [...], subtotal, tax_rate, notes, payment_terms}
    frequency: Mapped[str] = mapped_column(
        String(20), nullable=False, default="monthly",
    )
    # monthly | quarterly | annual
    next_issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
