"""
VEXX AI — Business Context Service

Funções que consultam o banco de dados e retornam métricas reais do negócio
para alimentar o assistente de IA com contexto empresarial.
"""
from datetime import date, timedelta
from sqlalchemy import func
from database.db import db
from database.models import (
    Contact, Lead, Transaction, Invoice, Automation, User
)
from utils.helpers import current_month_range


# ── Métricas financeiras ─────────────────────────────────────────────────────

def get_monthly_revenue(user_id: int) -> float:
    first, last = current_month_range()
    total = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == 'income',
        Transaction.date >= first, Transaction.date <= last,
    ).scalar()
    return round(float(total or 0), 2)


def get_monthly_expenses(user_id: int) -> float:
    first, last = current_month_range()
    total = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == 'expense',
        Transaction.date >= first, Transaction.date <= last,
    ).scalar()
    return round(float(total or 0), 2)


def get_profit_margin(user_id: int) -> dict:
    revenue = get_monthly_revenue(user_id)
    expenses = get_monthly_expenses(user_id)
    profit = revenue - expenses
    margin = (profit / revenue * 100) if revenue > 0 else 0
    return {
        'revenue': revenue, 'expenses': expenses,
        'profit': round(profit, 2), 'margin_pct': round(margin, 1),
    }


def get_quarterly_revenue(user_id: int) -> dict:
    today = date.today()
    quarter = (today.month - 1) // 3
    q_start = date(today.year, quarter * 3 + 1, 1)
    total = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == 'income',
        Transaction.date >= q_start, Transaction.date <= today,
    ).scalar()
    return {
        'quarter': quarter + 1,
        'year': today.year,
        'revenue': round(float(total or 0), 2),
    }


def get_top_revenue_categories(user_id: int, limit: int = 5) -> list:
    rows = db.session.query(
        Transaction.category, func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.user_id == user_id, Transaction.type == 'income',
    ).group_by(Transaction.category).order_by(func.sum(Transaction.amount).desc()).limit(limit).all()
    return [{'category': r.category or 'Sem categoria', 'total': round(float(r.total), 2)} for r in rows]


def get_pending_invoices(user_id: int) -> dict:
    invoices = Invoice.query.filter_by(user_id=user_id, status='pending').all()
    return {
        'count': len(invoices),
        'total': round(sum(i.amount for i in invoices), 2),
    }


# ── Métricas de CRM ──────────────────────────────────────────────────────────

def get_contacts_count(user_id: int) -> int:
    return Contact.query.filter_by(user_id=user_id).count()


def get_new_leads(user_id: int, days: int = 30) -> int:
    cutoff = date.today() - timedelta(days=days)
    return Lead.query.filter(
        Lead.user_id == user_id,
        Lead.created_at >= cutoff,
    ).count()


def get_pipeline_summary(user_id: int) -> dict:
    stages = ['prospect', 'qualified', 'proposal', 'negotiation', 'closed_won', 'closed_lost']
    by_stage = {}
    for s in stages:
        leads = Lead.query.filter_by(user_id=user_id, stage=s).all()
        by_stage[s] = {
            'count': len(leads),
            'total_value': round(sum(l.value for l in leads), 2),
        }
    active_value = sum(by_stage[s]['total_value'] for s in stages if s not in ('closed_won', 'closed_lost'))
    return {
        'by_stage': by_stage,
        'active_value': round(active_value, 2),
        'total_leads': sum(by_stage[s]['count'] for s in stages),
    }


def get_conversion_rate(user_id: int) -> dict:
    won = Lead.query.filter_by(user_id=user_id, stage='closed_won').count()
    lost = Lead.query.filter_by(user_id=user_id, stage='closed_lost').count()
    closed = won + lost
    rate = round((won / closed * 100), 1) if closed else 0
    return {'won': won, 'lost': lost, 'closed': closed, 'rate_pct': rate}


def get_top_leads_by_value(user_id: int, limit: int = 5) -> list:
    leads = Lead.query.filter_by(user_id=user_id).filter(
        Lead.stage.notin_(['closed_won', 'closed_lost'])
    ).order_by(Lead.value.desc()).limit(limit).all()
    return [{
        'title': l.title, 'value': l.value,
        'stage': l.stage, 'probability': l.probability,
    } for l in leads]


# ── Crescimento e tendências ─────────────────────────────────────────────────

def get_growth_metrics(user_id: int) -> dict:
    today = date.today()
    last_30 = today - timedelta(days=30)
    prev_60 = today - timedelta(days=60)

    contacts_30 = Contact.query.filter(
        Contact.user_id == user_id, Contact.created_at >= last_30
    ).count()
    contacts_prev = Contact.query.filter(
        Contact.user_id == user_id,
        Contact.created_at >= prev_60, Contact.created_at < last_30,
    ).count()

    rev_30 = float(db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id, Transaction.type == 'income',
        Transaction.date >= last_30,
    ).scalar() or 0)
    rev_prev = float(db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id, Transaction.type == 'income',
        Transaction.date >= prev_60, Transaction.date < last_30,
    ).scalar() or 0)

    def pct(curr, prev):
        if prev == 0: return 100.0 if curr > 0 else 0.0
        return round(((curr - prev) / prev) * 100, 1)

    return {
        'contacts_30d': contacts_30, 'contacts_growth_pct': pct(contacts_30, contacts_prev),
        'revenue_30d': round(rev_30, 2), 'revenue_growth_pct': pct(rev_30, rev_prev),
    }


# ── Automações ───────────────────────────────────────────────────────────────

def get_automation_stats(user_id: int) -> dict:
    total = Automation.query.filter_by(user_id=user_id).count()
    active = Automation.query.filter_by(user_id=user_id, enabled=True).count()
    runs = db.session.query(func.sum(Automation.runs_count)).filter_by(user_id=user_id).scalar() or 0
    return {'total': total, 'active': active, 'total_runs': int(runs)}


# ── Snapshot completo ────────────────────────────────────────────────────────

def get_business_summary(user_id: int) -> dict:
    """Snapshot completo do negócio para alimentar o system prompt."""
    user = User.query.get(user_id)
    margin = get_profit_margin(user_id)
    pipeline = get_pipeline_summary(user_id)
    conv = get_conversion_rate(user_id)
    growth = get_growth_metrics(user_id)
    quarter = get_quarterly_revenue(user_id)
    pending = get_pending_invoices(user_id)
    automations = get_automation_stats(user_id)
    categories = get_top_revenue_categories(user_id, 3)

    return {
        'company': user.company or 'Não informado',
        'plan': user.plan,
        'finance': {
            'month_revenue': margin['revenue'],
            'month_expenses': margin['expenses'],
            'month_profit': margin['profit'],
            'profit_margin_pct': margin['margin_pct'],
            'quarter_revenue': quarter['revenue'],
            'quarter_label': f"Q{quarter['quarter']}/{quarter['year']}",
            'pending_invoices_count': pending['count'],
            'pending_invoices_total': pending['total'],
            'top_revenue_categories': categories,
        },
        'crm': {
            'total_contacts': get_contacts_count(user_id),
            'new_leads_30d': get_new_leads(user_id, 30),
            'active_pipeline_value': pipeline['active_value'],
            'total_leads': pipeline['total_leads'],
            'conversion_rate_pct': conv['rate_pct'],
            'leads_won': conv['won'],
            'leads_lost': conv['lost'],
        },
        'growth': {
            'contacts_growth_30d_pct': growth['contacts_growth_pct'],
            'revenue_growth_30d_pct': growth['revenue_growth_pct'],
        },
        'automations': automations,
    }
