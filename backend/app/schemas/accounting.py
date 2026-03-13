"""VULKRAN OS — Accounting schemas."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class InvoiceItem(BaseModel):
    description: str
    quantity: int = 1
    unit_price: Decimal
    total: Decimal | None = None


class InvoiceCreate(BaseModel):
    client_id: uuid.UUID
    issue_date: date
    due_date: date
    items: list[InvoiceItem]
    tax_rate: Decimal = Decimal("21.00")
    notes: str | None = None


class InvoiceResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    invoice_number: str
    issue_date: date
    due_date: date
    status: str
    subtotal: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total: Decimal
    items: list | dict  # JSONB: list of item dicts
    notes: str | None = None
    pdf_path: str | None = None
    paid_at: datetime | None = None
    payment_method: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceMarkPaid(BaseModel):
    payment_method: str = "transfer"


class ExpenseCreate(BaseModel):
    description: str
    category: str
    amount: Decimal
    date: date
    vendor: str | None = None
    tax_deductible: bool = True
    notes: str | None = None
    client_id: uuid.UUID | None = None


class ExpenseResponse(BaseModel):
    id: uuid.UUID
    description: str
    category: str
    amount: Decimal
    tax_deductible: bool
    date: date
    vendor: str | None = None
    receipt_path: str | None = None
    notes: str | None = None
    client_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FinancialSummary(BaseModel):
    period: str
    total_invoiced: Decimal
    total_paid: Decimal
    total_pending: Decimal
    total_overdue: Decimal
    total_expenses: Decimal
    net_income: Decimal
    tax_collected: Decimal
    invoices_count: int
    expenses_count: int
