"""
VEXX AI — Background scheduler (APScheduler in-process).
Executa automações com triggers schedule_daily / schedule_weekly / schedule_monthly
e dispara verificações periódicas (faturas vencendo etc.).

Boot via init_scheduler(app) em main.py.
"""

import logging
from datetime import date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger('vexx.scheduler')

_scheduler: BackgroundScheduler | None = None


def init_scheduler(app):
    global _scheduler
    if _scheduler:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone='America/Sao_Paulo', daemon=True)

    # Diário 08:00
    _scheduler.add_job(
        lambda: _fire_event(app, 'schedule_daily'),
        CronTrigger(hour=8, minute=0),
        id='daily_8am', replace_existing=True,
    )
    # Semanal segunda 09:00
    _scheduler.add_job(
        lambda: _fire_event(app, 'schedule_weekly'),
        CronTrigger(day_of_week='mon', hour=9, minute=0),
        id='weekly_mon_9am', replace_existing=True,
    )
    # Mensal dia 1 09:00
    _scheduler.add_job(
        lambda: _fire_event(app, 'schedule_monthly'),
        CronTrigger(day=1, hour=9, minute=0),
        id='monthly_day1', replace_existing=True,
    )
    # Verificação de faturas vencendo a cada hora
    _scheduler.add_job(
        lambda: _check_invoices(app),
        CronTrigger(minute=0),
        id='invoice_check', replace_existing=True,
    )

    _scheduler.start()
    logger.info('VEXX scheduler iniciado com 4 jobs.')
    return _scheduler


def _fire_event(app, event):
    """Dispara `event` para TODOS os usuários (todas as automações ativas)."""
    from database.models import User
    from services.automation_service import trigger_event

    with app.app_context():
        users = User.query.filter_by(is_active=True).all()
        total = 0
        for u in users:
            total += trigger_event(u.id, event, {'scheduled': True, 'event': event})
        logger.info(f'[{event}] disparado para {len(users)} usuários, {total} automações executadas.')


def _check_invoices(app):
    """Verifica faturas que vencem em 3 dias e disparou o evento invoice_due,
    e marca como overdue + dispara invoice_overdue para vencidas."""
    from database.db import db
    from database.models import Invoice
    from services.automation_service import trigger_event

    with app.app_context():
        today = date.today()
        soon  = today + timedelta(days=3)

        # invoice_due (vencendo em 3 dias)
        due_soon = Invoice.query.filter(
            Invoice.status == 'pending',
            Invoice.due_date == soon,
        ).all()
        for inv in due_soon:
            trigger_event(inv.user_id, 'invoice_due', _invoice_ctx(inv))

        # marca overdue + dispara
        overdue = Invoice.query.filter(
            Invoice.status == 'pending',
            Invoice.due_date < today,
        ).all()
        for inv in overdue:
            inv.status = 'overdue'
        if overdue:
            db.session.commit()
        for inv in overdue:
            trigger_event(inv.user_id, 'invoice_overdue', _invoice_ctx(inv))

        if due_soon or overdue:
            logger.info(f'[invoice_check] {len(due_soon)} due_soon, {len(overdue)} overdue')


def _invoice_ctx(inv):
    return {
        'invoice': {
            'id': inv.id,
            'number': inv.invoice_number,
            'amount': inv.amount,
            'due_date': inv.due_date.isoformat() if inv.due_date else None,
            'description': inv.description,
        }
    }


def shutdown_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
