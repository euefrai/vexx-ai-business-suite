from datetime import date
from sqlalchemy import func
from database.db import db
from database.models import Transaction, Invoice
from utils.validators import sanitize_string, validate_required
from utils.helpers import current_month_range


def list_transactions(user_id: int, tx_type: str = '', limit: int = 50) -> list:
    q = Transaction.query.filter_by(user_id=user_id)
    if tx_type:
        q = q.filter_by(type=tx_type)
    return [t.to_dict() for t in q.order_by(Transaction.date.desc()).limit(limit).all()]


def create_transaction(user_id: int, data: dict) -> tuple[bool, str, dict | None]:
    ok, msg = validate_required(data, ['type', 'amount', 'description'])
    if not ok:
        return False, msg, None

    if data['type'] not in ('income', 'expense'):
        return False, 'Tipo inválido. Use "income" ou "expense".', None

    tx_date = date.today()
    if data.get('date'):
        try:
            tx_date = date.fromisoformat(data['date'])
        except ValueError:
            pass

    tx = Transaction(
        user_id=user_id,
        type=data['type'],
        amount=abs(float(data['amount'])),
        description=sanitize_string(data['description'], 200),
        category=sanitize_string(data.get('category', ''), 50),
        date=tx_date,
    )
    db.session.add(tx)
    db.session.commit()

    try:
        from services.automation_service import trigger_event
        ctx = {'transaction': tx.to_dict()}
        if tx.type == 'income':
            trigger_event(user_id, 'payment_received', ctx)
            if tx.amount >= 10000:
                trigger_event(user_id, 'revenue_above', ctx)
        elif tx.amount >= 5000:
            trigger_event(user_id, 'expense_above', ctx)
    except Exception:
        pass

    return True, 'Transação registrada.', tx.to_dict()


def delete_transaction(user_id: int, tx_id: int) -> tuple[bool, str]:
    tx = Transaction.query.filter_by(id=tx_id, user_id=user_id).first()
    if not tx:
        return False, 'Transação não encontrada.'
    db.session.delete(tx)
    db.session.commit()
    return True, 'Transação removida.'


def get_financial_summary(user_id: int) -> dict:
    first, last = current_month_range()
    income = _sum(user_id, 'income', first, last)
    expenses = _sum(user_id, 'expense', first, last)
    total_income = _sum(user_id, 'income')
    total_expenses = _sum(user_id, 'expense')

    pending_invoices = Invoice.query.filter_by(user_id=user_id, status='pending').all()
    pending_total = sum(i.amount for i in pending_invoices)

    return {
        'month_income': round(income, 2),
        'month_expenses': round(expenses, 2),
        'month_profit': round(income - expenses, 2),
        'total_income': round(total_income, 2),
        'total_expenses': round(total_expenses, 2),
        'balance': round(total_income - total_expenses, 2),
        'pending_invoices': len(pending_invoices),
        'pending_amount': round(pending_total, 2),
    }


def _sum(user_id, tx_type, start=None, end=None):
    q = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == tx_type,
    )
    if start:
        q = q.filter(Transaction.date >= start)
    if end:
        q = q.filter(Transaction.date <= end)
    return float(q.scalar() or 0)


def list_invoices(user_id: int, status: str = '') -> list:
    q = Invoice.query.filter_by(user_id=user_id)
    if status:
        q = q.filter_by(status=status)
    return [i.to_dict() for i in q.order_by(Invoice.created_at.desc()).all()]


def create_invoice(user_id: int, data: dict) -> tuple[bool, str, dict | None]:
    ok, msg = validate_required(data, ['amount'])
    if not ok:
        return False, msg, None

    count = Invoice.query.filter_by(user_id=user_id).count() + 1
    from utils.security import generate_invoice_number
    inv_number = generate_invoice_number(user_id, count)

    due_date = None
    if data.get('due_date'):
        try:
            due_date = date.fromisoformat(data['due_date'])
        except ValueError:
            pass

    invoice = Invoice(
        user_id=user_id,
        contact_id=data.get('contact_id'),
        invoice_number=inv_number,
        amount=float(data['amount']),
        status=data.get('status', 'pending'),
        due_date=due_date,
        description=sanitize_string(data.get('description', ''), 300),
    )
    db.session.add(invoice)
    db.session.commit()
    return True, 'Fatura criada.', invoice.to_dict()


def update_invoice_status(user_id: int, invoice_id: int, status: str) -> tuple[bool, str]:
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=user_id).first()
    if not invoice:
        return False, 'Fatura não encontrada.'
    if status not in ('pending', 'paid', 'overdue'):
        return False, 'Status inválido.'
    old = invoice.status
    invoice.status = status
    db.session.commit()

    try:
        from services.automation_service import trigger_event
        ctx = {'invoice': {
            'id': invoice.id, 'number': invoice.invoice_number,
            'amount': invoice.amount, 'description': invoice.description,
        }}
        if old != 'paid' and status == 'paid':
            trigger_event(user_id, 'payment_received', ctx)
        elif status == 'overdue':
            trigger_event(user_id, 'invoice_overdue', ctx)
    except Exception:
        pass

    return True, 'Fatura atualizada.'
