from datetime import datetime, date
from sqlalchemy import func
from database.db import db
from database.models import Contact, Lead, Transaction, Invoice, Automation, AIConversation
from utils.helpers import current_month_range, percentage_change


def get_dashboard_stats(user_id: int) -> dict:
    now = date.today()
    first_day, last_day = current_month_range()

    prev_month = date(now.year, now.month - 1 if now.month > 1 else 12, 1)
    prev_first, prev_last = _month_range_for(prev_month.year, prev_month.month)

    revenue = _sum_transactions(user_id, 'income', first_day, last_day)
    prev_revenue = _sum_transactions(user_id, 'income', prev_first, prev_last)

    expenses = _sum_transactions(user_id, 'expense', first_day, last_day)
    profit = revenue - expenses

    total_contacts = Contact.query.filter_by(user_id=user_id).count()
    active_leads = Lead.query.filter_by(user_id=user_id).filter(
        Lead.stage.notin_(['closed_won', 'closed_lost'])
    ).count()
    leads_value = db.session.query(func.sum(Lead.value)).filter(
        Lead.user_id == user_id,
        Lead.stage.notin_(['closed_won', 'closed_lost'])
    ).scalar() or 0

    active_automations = Automation.query.filter_by(user_id=user_id, enabled=True).count()

    return {
        'revenue': round(revenue, 2),
        'revenue_change': percentage_change(revenue, prev_revenue),
        'expenses': round(expenses, 2),
        'profit': round(profit, 2),
        'total_contacts': total_contacts,
        'active_leads': active_leads,
        'leads_pipeline_value': round(leads_value, 2),
        'active_automations': active_automations,
    }


def get_recent_activity(user_id: int, limit: int = 10) -> list:
    events = []

    contacts = Contact.query.filter_by(user_id=user_id).order_by(Contact.created_at.desc()).limit(3).all()
    for c in contacts:
        events.append({'type': 'contact', 'icon': '👤', 'text': f'Novo contato: {c.name}', 'time': c.created_at})

    leads = Lead.query.filter_by(user_id=user_id).order_by(Lead.created_at.desc()).limit(3).all()
    for l in leads:
        events.append({'type': 'lead', 'icon': '🎯', 'text': f'Lead criado: {l.title}', 'time': l.created_at})

    txns = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.created_at.desc()).limit(3).all()
    for t in txns:
        kind = 'Receita' if t.type == 'income' else 'Despesa'
        events.append({'type': 'transaction', 'icon': '💰', 'text': f'{kind}: R$ {t.amount:.2f}', 'time': t.created_at})

    events.sort(key=lambda x: x['time'], reverse=True)
    return [
        {**e, 'time': e['time'].strftime('%d/%m %H:%M')}
        for e in events[:limit]
    ]


def get_monthly_revenue_chart(user_id: int) -> list:
    result = []
    today = date.today()
    for i in range(5, -1, -1):
        month = today.month - i
        year = today.year
        if month <= 0:
            month += 12
            year -= 1
        first, last = _month_range_for(year, month)
        rev = _sum_transactions(user_id, 'income', first, last)
        exp = _sum_transactions(user_id, 'expense', first, last)
        result.append({
            'label': first.strftime('%b'),
            'revenue': round(rev, 2),
            'expenses': round(exp, 2),
        })
    return result


def _sum_transactions(user_id, tx_type, start, end):
    from database.models import Transaction
    total = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == tx_type,
        Transaction.date >= start,
        Transaction.date <= end,
    ).scalar()
    return float(total or 0)


def _month_range_for(year, month):
    from calendar import monthrange
    first = date(year, month, 1)
    last = date(year, month, monthrange(year, month)[1])
    return first, last
