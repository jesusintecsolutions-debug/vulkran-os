"""VULKRAN OS — Accounting API endpoints (invoices + expenses)."""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models import Client
from app.models.accounting import Invoice, Expense
from app.schemas.accounting import (
    InvoiceCreate,
    InvoiceResponse,
    InvoiceMarkPaid,
    ExpenseCreate,
    ExpenseResponse,
    FinancialSummary,
)

router = APIRouter(prefix="/api/accounting", tags=["accounting"])


# ──────────────────────────────────────────────
# Invoice numbering
# ──────────────────────────────────────────────


async def _next_invoice_number(db: AsyncSession) -> str:
    """Generate next invoice number: VK-YYYY-NNN."""
    year = datetime.now(timezone.utc).year
    prefix = f"VK-{year}-"

    result = await db.scalar(
        select(func.count()).select_from(Invoice).where(
            Invoice.invoice_number.like(f"{prefix}%")
        )
    )
    seq = (result or 0) + 1
    return f"{prefix}{seq:03d}"


# ──────────────────────────────────────────────
# Invoices
# ──────────────────────────────────────────────


@router.get("/invoices", response_model=list[InvoiceResponse])
async def list_invoices(
    client_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(Invoice).order_by(Invoice.issue_date.desc())
    if client_id:
        query = query.where(Invoice.client_id == client_id)
    if status:
        query = query.where(Invoice.status == status)
    query = query.limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/invoices", response_model=InvoiceResponse, status_code=201)
async def create_invoice(
    body: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    # Verify client
    result = await db.execute(select(Client).where(Client.id == body.client_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Client not found")

    # Calculate totals
    items_data = []
    subtotal = Decimal("0")
    for item in body.items:
        item_total = item.unit_price * item.quantity
        items_data.append({
            "description": item.description,
            "quantity": item.quantity,
            "unit_price": str(item.unit_price),
            "total": str(item_total),
        })
        subtotal += item_total

    tax_amount = (subtotal * body.tax_rate / Decimal("100")).quantize(Decimal("0.01"))
    total = subtotal + tax_amount

    invoice_number = await _next_invoice_number(db)

    invoice = Invoice(
        client_id=body.client_id,
        invoice_number=invoice_number,
        issue_date=body.issue_date,
        due_date=body.due_date,
        status="draft",
        subtotal=subtotal,
        tax_rate=body.tax_rate,
        tax_amount=tax_amount,
        total=total,
        items=items_data,
        notes=body.notes,
    )
    db.add(invoice)
    await db.flush()
    return invoice


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    return invoice


@router.post("/invoices/{invoice_id}/send", response_model=InvoiceResponse)
async def send_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Mark invoice as sent."""
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    if invoice.status != "draft":
        raise HTTPException(400, f"Cannot send: invoice is '{invoice.status}'")
    invoice.status = "sent"
    await db.flush()
    return invoice


@router.post("/invoices/{invoice_id}/pay", response_model=InvoiceResponse)
async def mark_paid(
    invoice_id: uuid.UUID,
    body: InvoiceMarkPaid,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Mark invoice as paid."""
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    if invoice.status in ("paid", "cancelled"):
        raise HTTPException(400, f"Cannot pay: invoice is '{invoice.status}'")
    invoice.status = "paid"
    invoice.paid_at = datetime.now(timezone.utc)
    invoice.payment_method = body.payment_method
    await db.flush()
    return invoice


# ──────────────────────────────────────────────
# Expenses
# ──────────────────────────────────────────────


@router.get("/expenses", response_model=list[ExpenseResponse])
async def list_expenses(
    category: str | None = None,
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(Expense).order_by(Expense.date.desc())
    if category:
        query = query.where(Expense.category == category)
    query = query.limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/expenses", response_model=ExpenseResponse, status_code=201)
async def create_expense(
    body: ExpenseCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    expense = Expense(**body.model_dump())
    db.add(expense)
    await db.flush()
    return expense


# ──────────────────────────────────────────────
# Financial Summary
# ──────────────────────────────────────────────


@router.get("/summary", response_model=FinancialSummary)
async def financial_summary(
    year: int = Query(default=None),
    month: int = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Get financial summary for a given month or current month."""
    now = datetime.now(timezone.utc)
    y = year or now.year
    m = month or now.month

    # Invoice aggregates
    def invoice_filter(query):
        return query.where(
            extract("year", Invoice.issue_date) == y,
            extract("month", Invoice.issue_date) == m,
        )

    total_invoiced = await db.scalar(
        invoice_filter(select(func.coalesce(func.sum(Invoice.total), 0)).select_from(Invoice))
    ) or Decimal("0")

    total_paid = await db.scalar(
        invoice_filter(
            select(func.coalesce(func.sum(Invoice.total), 0)).select_from(Invoice)
            .where(Invoice.status == "paid")
        )
    ) or Decimal("0")

    total_overdue = await db.scalar(
        invoice_filter(
            select(func.coalesce(func.sum(Invoice.total), 0)).select_from(Invoice)
            .where(Invoice.status == "overdue")
        )
    ) or Decimal("0")

    total_pending = total_invoiced - total_paid - total_overdue

    tax_collected = await db.scalar(
        invoice_filter(
            select(func.coalesce(func.sum(Invoice.tax_amount), 0)).select_from(Invoice)
            .where(Invoice.status == "paid")
        )
    ) or Decimal("0")

    invoices_count = await db.scalar(
        invoice_filter(select(func.count()).select_from(Invoice))
    ) or 0

    # Expense aggregates
    total_expenses = await db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).select_from(Expense).where(
            extract("year", Expense.date) == y,
            extract("month", Expense.date) == m,
        )
    ) or Decimal("0")

    expenses_count = await db.scalar(
        select(func.count()).select_from(Expense).where(
            extract("year", Expense.date) == y,
            extract("month", Expense.date) == m,
        )
    ) or 0

    return FinancialSummary(
        period=f"{y}-{m:02d}",
        total_invoiced=total_invoiced,
        total_paid=total_paid,
        total_pending=total_pending,
        total_overdue=total_overdue,
        total_expenses=total_expenses,
        net_income=total_paid - total_expenses,
        tax_collected=tax_collected,
        invoices_count=invoices_count,
        expenses_count=expenses_count,
    )
