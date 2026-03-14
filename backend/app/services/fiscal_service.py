"""VULKRAN OS — Spanish fiscal engine.

Handles:
- IVA calculation (21% general, 10% reduced, 4% super-reduced)
- IRPF withholding (15% standard, 7% new autonomos)
- Modelo 303 (quarterly VAT return)
- Modelo 130 (quarterly IRPF prepayment)
- Tax calendar with alerts
- Cash flow projections
"""

import logging
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting import Invoice, Expense
from app.models.fiscal import FiscalConfig, TaxObligation

logger = logging.getLogger(__name__)

# Spanish tax rates
IVA_GENERAL = Decimal("21.00")
IVA_REDUCIDO = Decimal("10.00")
IVA_SUPERREDUCIDO = Decimal("4.00")
IVA_EXENTO = Decimal("0.00")

IRPF_STANDARD = Decimal("15.00")
IRPF_NEW_AUTONOMO = Decimal("7.00")

# Tax calendar — filing deadlines (day of month)
TAX_DEADLINES = {
    1: date(2026, 4, 20),   # Q1 deadline
    2: date(2026, 7, 20),   # Q2 deadline
    3: date(2026, 10, 20),  # Q3 deadline
    4: date(2027, 1, 30),   # Q4 deadline
}


async def calculate_modelo_303(
    db: AsyncSession,
    client_id: str,
    year: int,
    quarter: int,
) -> dict:
    """
    Calculate Modelo 303 (quarterly VAT return).

    Formula: IVA Repercutido (charged on invoices) - IVA Soportado (paid on expenses)
    Positive = must pay to Hacienda
    Negative = to be refunded (only in Q4 or via special request)
    """
    # Quarter date range
    quarter_start = date(year, (quarter - 1) * 3 + 1, 1)
    if quarter == 4:
        quarter_end = date(year, 12, 31)
    else:
        quarter_end = date(year, quarter * 3 + 1, 1) - timedelta(days=1)

    # IVA Repercutido — from invoices issued
    invoices_result = await db.execute(
        select(
            func.coalesce(func.sum(Invoice.tax_amount), 0),
            func.coalesce(func.sum(Invoice.subtotal), 0),
        )
        .where(
            Invoice.client_id == client_id,
            Invoice.issue_date >= quarter_start,
            Invoice.issue_date <= quarter_end,
            Invoice.status != "cancelled",
        )
    )
    iva_repercutido, base_imponible = invoices_result.one()
    iva_repercutido = Decimal(str(iva_repercutido))
    base_imponible = Decimal(str(base_imponible))

    # IVA Soportado — from deductible expenses
    expenses_result = await db.execute(
        select(func.coalesce(func.sum(Expense.amount), 0))
        .where(
            Expense.client_id == client_id,
            Expense.date >= quarter_start,
            Expense.date <= quarter_end,
            Expense.tax_deductible.is_(True),
        )
    )
    total_expenses = Decimal(str(expenses_result.scalar()))
    iva_soportado = total_expenses * IVA_GENERAL / 100  # Simplified — assumes 21% on all

    resultado = iva_repercutido - iva_soportado

    return {
        "type": "modelo_303",
        "year": year,
        "quarter": quarter,
        "period": f"Q{quarter}",
        "base_imponible": float(base_imponible),
        "iva_repercutido": float(iva_repercutido),
        "iva_soportado": float(iva_soportado),
        "resultado": float(resultado),
        "a_ingresar": float(max(resultado, 0)),
        "a_devolver": float(abs(min(resultado, 0))),
    }


async def calculate_modelo_130(
    db: AsyncSession,
    client_id: str,
    year: int,
    quarter: int,
) -> dict:
    """
    Calculate Modelo 130 (quarterly IRPF prepayment for autonomos).

    Formula: 20% × (ingresos - gastos) - retenciones soportadas - pagos anteriores
    """
    quarter_start = date(year, (quarter - 1) * 3 + 1, 1)
    if quarter == 4:
        quarter_end = date(year, 12, 31)
    else:
        quarter_end = date(year, quarter * 3 + 1, 1) - timedelta(days=1)

    # Year-to-date income (cumulative from Jan 1)
    ytd_start = date(year, 1, 1)

    income_result = await db.execute(
        select(func.coalesce(func.sum(Invoice.subtotal), 0))
        .where(
            Invoice.client_id == client_id,
            Invoice.issue_date >= ytd_start,
            Invoice.issue_date <= quarter_end,
            Invoice.status != "cancelled",
        )
    )
    ytd_income = Decimal(str(income_result.scalar()))

    expenses_result = await db.execute(
        select(func.coalesce(func.sum(Expense.amount), 0))
        .where(
            Expense.client_id == client_id,
            Expense.date >= ytd_start,
            Expense.date <= quarter_end,
            Expense.tax_deductible.is_(True),
        )
    )
    ytd_expenses = Decimal(str(expenses_result.scalar()))

    net_income = ytd_income - ytd_expenses
    pago_fraccionado = net_income * Decimal("0.20")

    # TODO: subtract previous quarterly payments and withholdings
    resultado = max(pago_fraccionado, Decimal("0"))

    return {
        "type": "modelo_130",
        "year": year,
        "quarter": quarter,
        "period": f"Q{quarter}",
        "ytd_income": float(ytd_income),
        "ytd_expenses": float(ytd_expenses),
        "net_income": float(net_income),
        "pago_fraccionado_20pct": float(pago_fraccionado),
        "resultado": float(resultado),
    }


async def get_tax_calendar(
    db: AsyncSession,
    client_id: str,
    year: int | None = None,
) -> list[dict]:
    """Get upcoming tax obligations with deadlines."""
    if year is None:
        year = date.today().year

    result = await db.execute(
        select(TaxObligation)
        .where(
            TaxObligation.client_id == client_id,
            TaxObligation.year == year,
        )
        .order_by(TaxObligation.due_date)
    )
    obligations = result.scalars().all()

    calendar = []
    for ob in obligations:
        days_until = (ob.due_date - date.today()).days
        calendar.append({
            "id": str(ob.id),
            "type": ob.obligation_type,
            "period": ob.period,
            "due_date": ob.due_date.isoformat(),
            "status": ob.status,
            "amount": float(ob.amount) if ob.amount else None,
            "days_until_due": days_until,
            "urgent": days_until <= 15 and ob.status in ("pending", "calculated"),
        })

    return calendar


async def get_cashflow_projection(
    db: AsyncSession,
    client_id: str,
    months: int = 6,
) -> list[dict]:
    """Project cash flow based on invoices, expenses, and tax obligations."""
    today = date.today()
    projection = []

    for i in range(months):
        month = today.month + i
        year = today.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year, 12, 31)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)

        # Expected income — invoices due
        income_result = await db.execute(
            select(func.coalesce(func.sum(Invoice.total), 0))
            .where(
                Invoice.client_id == client_id,
                Invoice.due_date >= month_start,
                Invoice.due_date <= month_end,
                Invoice.status.in_(["sent", "draft"]),
            )
        )
        expected_income = float(income_result.scalar())

        # Expected expenses (use monthly average if no specific data)
        expense_result = await db.execute(
            select(func.coalesce(func.sum(Expense.amount), 0))
            .where(
                Expense.client_id == client_id,
                Expense.date >= month_start,
                Expense.date <= month_end,
            )
        )
        expected_expenses = float(expense_result.scalar())

        # Tax obligations due this month
        tax_result = await db.execute(
            select(func.coalesce(func.sum(TaxObligation.amount), 0))
            .where(
                TaxObligation.client_id == client_id,
                TaxObligation.due_date >= month_start,
                TaxObligation.due_date <= month_end,
                TaxObligation.status.in_(["pending", "calculated"]),
            )
        )
        tax_due = float(tax_result.scalar())

        net = expected_income - expected_expenses - tax_due

        projection.append({
            "month": f"{year}-{month:02d}",
            "expected_income": expected_income,
            "expected_expenses": expected_expenses,
            "tax_obligations": tax_due,
            "net_cashflow": net,
        })

    return projection
