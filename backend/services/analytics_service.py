from datetime import date, timedelta
from sqlalchemy import func
from database.db import db
from database.models import Contact, Lead, Transaction, Automation


def get_analytics_overview(user_id: int) -> dict:
    today = date.today()
    last_30 = today - timedelta(days=30)
    last_60 = today - timedelta(days=60)

    contacts_30 = Contact.query.filter(
        Contact.user_id == user_id,
        Contact.created_at >= last_30
    ).count()
    contacts_60 = Contact.query.filter(
        Contact.user_id == user_id,
        Contact.created_at >= last_60,
        Contact.created_at < last_30
    ).count()

    leads_won = Lead.query.filter_by(user_id=user_id, stage='closed_won').count()
    leads_lost = Lead.query.filter_by(user_id=user_id, stage='closed_lost').count()
    total_closed = leads_won + leads_lost
    conversion_rate = round((leads_won / total_closed * 100) if total_closed > 0 else 0, 1)

    revenue_30 = _sum_income(user_id, last_30, today)
    revenue_60 = _sum_income(user_id, last_60, last_30)
    revenue_growth = _change(revenue_30, revenue_60)

    return {
        'contacts_30d': contacts_30,
        'contacts_growth': _change(contacts_30, contacts_60),
        'conversion_rate': conversion_rate,
        'revenue_30d': round(revenue_30, 2),
        'revenue_growth': revenue_growth,
        'leads_won': leads_won,
        'leads_lost': leads_lost,
        'total_leads': Lead.query.filter_by(user_id=user_id).count(),
    }


def get_leads_by_stage(user_id: int) -> list:
    stages = ['prospect', 'qualified', 'proposal', 'negotiation', 'closed_won', 'closed_lost']
    result = []
    for stage in stages:
        count = Lead.query.filter_by(user_id=user_id, stage=stage).count()
        result.append({'stage': stage, 'count': count})
    return result


def get_revenue_trend(user_id: int, days: int = 30) -> list:
    today = date.today()
    result = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        income = _sum_income(user_id, d, d)
        expenses = _sum_expense(user_id, d, d)
        result.append({
            'date': d.strftime('%d/%m'),
            'income': round(income, 2),
            'expenses': round(expenses, 2),
        })
    return result


def get_top_categories(user_id: int) -> list:
    rows = db.session.query(
        Transaction.category,
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.user_id == user_id,
        Transaction.type == 'income'
    ).group_by(Transaction.category).order_by(func.sum(Transaction.amount).desc()).limit(5).all()
    return [{'category': r.category or 'Sem categoria', 'total': round(float(r.total), 2)} for r in rows]


def _sum_income(user_id, start, end):
    result = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == 'income',
        Transaction.date >= start,
        Transaction.date <= end,
    ).scalar()
    return float(result or 0)


def _sum_expense(user_id, start, end):
    result = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == 'expense',
        Transaction.date >= start,
        Transaction.date <= end,
    ).scalar()
    return float(result or 0)


def _change(current, previous):
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)
