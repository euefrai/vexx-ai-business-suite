"""
VEXX AI — Automation engine service.
Workflows, execução simulada, logs estruturados, templates e sugestões IA.
"""

import json
import time
from datetime import datetime, timedelta
from database.db import db
from database.models import Automation, AutomationLog, Contact, Lead, Transaction, Invoice
from utils.validators import sanitize_string, validate_required


# ═══════════════════════════════════════════════════════════════════════════════
# Triggers / Actions disponíveis (vão alimentar o workflow builder)
# ═══════════════════════════════════════════════════════════════════════════════

TRIGGERS = [
    {'id': 'new_contact',         'label': 'Novo contato cadastrado',     'icon': 'user-plus'},
    {'id': 'new_lead',            'label': 'Novo lead criado',            'icon': 'target'},
    {'id': 'lead_won',            'label': 'Lead ganho',                  'icon': 'check-circle'},
    {'id': 'lead_lost',           'label': 'Lead perdido',                'icon': 'x-circle'},
    {'id': 'lead_stage_change',   'label': 'Mudança de estágio do lead',  'icon': 'git-branch'},
    {'id': 'payment_received',    'label': 'Pagamento recebido',          'icon': 'dollar-sign'},
    {'id': 'invoice_overdue',     'label': 'Fatura vencida',              'icon': 'alert-triangle'},
    {'id': 'invoice_due',         'label': 'Fatura vencendo (3 dias)',    'icon': 'clock'},
    {'id': 'revenue_above',       'label': 'Receita acima de X',          'icon': 'trending-up'},
    {'id': 'expense_above',       'label': 'Despesa acima de X',          'icon': 'trending-down'},
    {'id': 'message_received',    'label': 'Mensagem recebida (chat)',    'icon': 'message-circle'},
    {'id': 'incoming_webhook',    'label': 'Webhook recebido',            'icon': 'webhook'},
    {'id': 'schedule_daily',      'label': 'Diário (08:00)',              'icon': 'clock'},
    {'id': 'schedule_weekly',     'label': 'Semanal (segunda 09:00)',     'icon': 'calendar'},
    {'id': 'schedule_monthly',    'label': 'Mensal (dia 1)',              'icon': 'calendar-days'},
    {'id': 'goal_missed',         'label': 'Meta não atingida',           'icon': 'target'},
    {'id': 'bank_transaction',    'label': 'Transação bancária (Open Finance)', 'icon': 'landmark'},
]

ACTIONS = [
    {'id': 'send_email',          'label': 'Enviar email',                'icon': 'mail'},
    {'id': 'send_whatsapp',       'label': 'Enviar WhatsApp',             'icon': 'message-circle'},
    {'id': 'send_telegram',       'label': 'Enviar Telegram',             'icon': 'send'},
    {'id': 'send_slack',          'label': 'Postar no Slack',             'icon': 'hash'},
    {'id': 'send_discord',        'label': 'Postar no Discord',           'icon': 'message-square'},
    {'id': 'create_task',         'label': 'Criar tarefa',                'icon': 'check-square'},
    {'id': 'update_lead_stage',   'label': 'Atualizar estágio de lead',   'icon': 'git-branch'},
    {'id': 'create_invoice',      'label': 'Criar fatura/cobrança',       'icon': 'file-text'},
    {'id': 'append_sheet',        'label': 'Adicionar linha em planilha', 'icon': 'table'},
    {'id': 'notify_team',         'label': 'Notificar equipe (interno)',  'icon': 'bell'},
    {'id': 'generate_report',     'label': 'Gerar relatório PDF',         'icon': 'file-text'},
    {'id': 'ai_insight',          'label': 'Gerar insight com IA',        'icon': 'bot'},
    {'id': 'call_webhook',        'label': 'Chamar webhook externo',      'icon': 'webhook'},
    {'id': 'sync_bank',           'label': 'Sincronizar banco',           'icon': 'banknote'},
]

TRIGGER_IDS = {item['id'] for item in TRIGGERS}
ACTION_IDS = {item['id'] for item in ACTIONS}


def _validate_config_actions(config: dict) -> tuple[bool, str]:
    steps = (config or {}).get('steps') or []
    for idx, step in enumerate(steps, 1):
        action_id = step.get('action')
        if action_id not in ACTION_IDS:
            return False, f'Ação inválida no passo {idx}.'
    return True, ''


# ═══════════════════════════════════════════════════════════════════════════════
# Templates prontos
# ═══════════════════════════════════════════════════════════════════════════════

TEMPLATES = [
    {
        'id': 'welcome_email',
        'name': 'Email de boas-vindas',
        'description': 'Quando um novo contato é cadastrado, envia um email de boas-vindas automaticamente.',
        'category': 'marketing',
        'icon': 'mail',
        'trigger': 'new_contact',
        'action': 'send_email',
        'tags': ['email', 'onboarding'],
    },
    {
        'id': 'lead_followup',
        'name': 'Follow-up de leads frios',
        'description': 'Notifica a equipe e dispara WhatsApp 3 dias após criação de um lead sem movimento.',
        'category': 'sales',
        'icon': 'target',
        'trigger': 'new_lead',
        'action': 'send_whatsapp',
        'tags': ['crm', 'whatsapp'],
    },
    {
        'id': 'invoice_reminder',
        'name': 'Lembrete de fatura',
        'description': 'Envia email 3 dias antes do vencimento da fatura.',
        'category': 'finance',
        'icon': 'file-text',
        'trigger': 'invoice_due',
        'action': 'send_email',
        'tags': ['finance', 'cobranca'],
    },
    {
        'id': 'overdue_alert',
        'name': 'Alerta de inadimplência',
        'description': 'WhatsApp + email quando fatura passa do vencimento.',
        'category': 'finance',
        'icon': 'alert-triangle',
        'trigger': 'invoice_overdue',
        'action': 'send_whatsapp',
        'tags': ['finance', 'cobranca'],
    },
    {
        'id': 'won_lead_celebration',
        'name': 'Comemorar venda fechada',
        'description': 'Notifica time no Slack quando um lead é marcado como ganho.',
        'category': 'sales',
        'icon': 'check-circle',
        'trigger': 'lead_won',
        'action': 'send_slack',
        'tags': ['slack', 'crm'],
    },
    {
        'id': 'weekly_report',
        'name': 'Relatório semanal',
        'description': 'Toda segunda às 9h, gera relatório executivo e envia por email.',
        'category': 'reports',
        'icon': 'bar-chart-3',
        'trigger': 'schedule_weekly',
        'action': 'generate_report',
        'tags': ['reports', 'agenda'],
    },
    {
        'id': 'daily_bank_sync',
        'name': 'Sincronização bancária diária',
        'description': 'Importa extrato bancário todo dia às 8h via Open Finance.',
        'category': 'finance',
        'icon': 'landmark',
        'trigger': 'schedule_daily',
        'action': 'sync_bank',
        'tags': ['banking', 'agenda'],
    },
    {
        'id': 'payment_thanks',
        'name': 'Agradecer pagamento recebido',
        'description': 'Quando Stripe/Mercado Pago notifica pagamento, envia WhatsApp de agradecimento.',
        'category': 'finance',
        'icon': 'dollar-sign',
        'trigger': 'payment_received',
        'action': 'send_whatsapp',
        'tags': ['payments', 'whatsapp'],
    },
    {
        'id': 'high_value_alert',
        'name': 'Alerta de receita alta',
        'description': 'Notifica gestor quando entrada > R$ 10.000.',
        'category': 'finance',
        'icon': 'trending-up',
        'trigger': 'revenue_above',
        'action': 'notify_team',
        'tags': ['finance', 'alert'],
    },
    {
        'id': 'goal_missed',
        'name': 'Meta não atingida',
        'description': 'Avisa fim do mês se receita ficou abaixo da meta.',
        'category': 'reports',
        'icon': 'target',
        'trigger': 'goal_missed',
        'action': 'ai_insight',
        'tags': ['reports', 'ai'],
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# CRUD de automações
# ═══════════════════════════════════════════════════════════════════════════════

def list_automations(user_id: int) -> list:
    return [a.to_dict() for a in
            Automation.query.filter_by(user_id=user_id).order_by(Automation.created_at.desc()).all()]


def create_automation(user_id: int, data: dict) -> tuple[bool, str, dict | None]:
    ok, msg = validate_required(data, ['name', 'trigger', 'action'])
    if not ok:
        return False, msg, None
    if data['trigger'] not in TRIGGER_IDS:
        return False, 'Gatilho inválido.', None
    if data['action'] not in ACTION_IDS:
        return False, 'Ação inválida.', None
    ok, msg = _validate_config_actions(data.get('config', {}))
    if not ok:
        return False, msg, None

    automation = Automation(
        user_id=user_id,
        name=sanitize_string(data['name'], 100),
        description=sanitize_string(data.get('description', ''), 300),
        trigger=data['trigger'],
        action=data['action'],
        config=json.dumps(data.get('config', {})),
        enabled=data.get('enabled', True),
    )
    db.session.add(automation)
    db.session.commit()
    _log(user_id, automation.id, 'success', automation.trigger, automation.action,
         f'Automação "{automation.name}" criada')
    return True, 'Automação criada.', automation.to_dict()


def update_automation(user_id: int, auto_id: int, data: dict) -> tuple[bool, str]:
    auto = Automation.query.filter_by(id=auto_id, user_id=user_id).first()
    if not auto:
        return False, 'Automação não encontrada.'
    if 'name' in data:        auto.name = sanitize_string(data['name'], 100)
    if 'description' in data: auto.description = sanitize_string(data['description'], 300)
    if 'trigger' in data:
        if data['trigger'] not in TRIGGER_IDS:
            return False, 'Gatilho inválido.'
        auto.trigger = data['trigger']
    if 'action' in data:
        if data['action'] not in ACTION_IDS:
            return False, 'Ação inválida.'
        auto.action = data['action']
    if 'config' in data:
        ok, msg = _validate_config_actions(data['config'])
        if not ok:
            return False, msg
        auto.config = json.dumps(data['config'])
    if 'enabled' in data:     auto.enabled = bool(data['enabled'])
    db.session.commit()
    return True, 'Automação atualizada.'


def toggle_automation(user_id: int, auto_id: int) -> tuple[bool, str, bool | None]:
    auto = Automation.query.filter_by(id=auto_id, user_id=user_id).first()
    if not auto:
        return False, 'Automação não encontrada.', None
    auto.enabled = not auto.enabled
    db.session.commit()
    return True, f'Automação {"ativada" if auto.enabled else "desativada"}.', auto.enabled


def delete_automation(user_id: int, auto_id: int) -> tuple[bool, str]:
    auto = Automation.query.filter_by(id=auto_id, user_id=user_id).first()
    if not auto:
        return False, 'Automação não encontrada.'
    db.session.delete(auto)
    db.session.commit()
    return True, 'Automação removida.'


def simulate_run(user_id: int, auto_id: int, context: dict | None = None) -> tuple[bool, str]:
    """
    Executa um workflow REAL (chama integrações), registra log estruturado.
    Suporta multi-step via auto.config['steps']. Quando não há steps,
    executa auto.action única.
    """
    from services.action_executor import execute as exec_action

    auto = Automation.query.filter_by(id=auto_id, user_id=user_id).first()
    if not auto:
        return False, 'Automação não encontrada.'
    if not auto.enabled:
        _log(user_id, auto.id, 'skipped', auto.trigger, auto.action,
             'Automação desativada — execução pulada')
        return False, 'Automação está desativada.'

    # Carrega steps (multi-step) ou cai no action único
    try:
        cfg = json.loads(auto.config or '{}')
    except Exception:
        cfg = {}

    steps = cfg.get('steps')
    if not steps:
        steps = [{'action': auto.action, 'params': cfg.get('params', {})}]

    started = time.time()
    auto.runs_count += 1
    auto.last_run = datetime.utcnow()
    db.session.commit()

    ctx = context or {}
    last_msg = ''
    overall_ok = True

    for idx, step in enumerate(steps, 1):
        action_id = step.get('action')
        params    = step.get('params', {})
        step_started = time.time()
        ok, msg = exec_action(user_id, action_id, params, ctx)
        step_ms = int((time.time() - step_started) * 1000)

        _log(user_id, auto.id,
             'success' if ok else 'error',
             auto.trigger, action_id,
             f'Step {idx}/{len(steps)}: {msg}', step_ms,
             {'context': ctx, 'params': params})

        if not ok:
            overall_ok = False
            last_msg = msg
            if cfg.get('stop_on_error', False):
                break
        else:
            last_msg = msg

    total_ms = int((time.time() - started) * 1000)
    _log(user_id, auto.id,
         'success' if overall_ok else 'error',
         auto.trigger, auto.action,
         f'Workflow "{auto.name}" finalizado ({len(steps)} step(s))',
         total_ms)

    return overall_ok, last_msg or f'Automação "{auto.name}" executada.'


# ═══════════════════════════════════════════════════════════════════════════════
# Stats
# ═══════════════════════════════════════════════════════════════════════════════

def get_automation_stats(user_id: int) -> dict:
    all_autos = Automation.query.filter_by(user_id=user_id).all()
    active = [a for a in all_autos if a.enabled]
    total_runs = sum(a.runs_count for a in all_autos)
    last_run = max((a.last_run for a in all_autos if a.last_run), default=None)

    # taxa de sucesso (últimos 100 logs)
    recent = AutomationLog.query.filter_by(user_id=user_id) \
        .order_by(AutomationLog.created_at.desc()).limit(100).all()
    if recent:
        ok_count = sum(1 for r in recent if r.status == 'success')
        success_rate = round((ok_count / len(recent)) * 100, 1)
    else:
        success_rate = 100.0

    return {
        'total': len(all_autos),
        'active': len(active),
        'total_runs': total_runs,
        'last_run': last_run.isoformat() if last_run else None,
        'success_rate': success_rate,
        'triggers': TRIGGERS,
        'actions': ACTIONS,
    }


def list_logs(user_id: int, limit: int = 100, status: str = '') -> list:
    q = AutomationLog.query.filter_by(user_id=user_id)
    if status:
        q = q.filter_by(status=status)
    logs = q.order_by(AutomationLog.created_at.desc()).limit(min(limit, 500)).all()
    return [l.to_dict() for l in logs]


# ═══════════════════════════════════════════════════════════════════════════════
# Templates
# ═══════════════════════════════════════════════════════════════════════════════

def list_templates() -> list:
    return TEMPLATES


def create_from_template(user_id: int, template_id: str) -> tuple[bool, str, dict | None]:
    tpl = next((t for t in TEMPLATES if t['id'] == template_id), None)
    if not tpl:
        return False, 'Template não encontrado.', None
    return create_automation(user_id, {
        'name': tpl['name'],
        'description': tpl['description'],
        'trigger': tpl['trigger'],
        'action': tpl['action'],
        'enabled': True,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# Sugestões IA — analisa contexto do usuário e propõe automações relevantes
# ═══════════════════════════════════════════════════════════════════════════════

def get_ai_suggestions(user_id: int) -> list:
    """
    Analisa o estado do negócio e devolve sugestões personalizadas
    de automações que fariam sentido criar agora.
    """
    suggestions = []

    overdue = Invoice.query.filter_by(user_id=user_id, status='overdue').count()
    pending = Invoice.query.filter_by(user_id=user_id, status='pending').count()
    contacts = Contact.query.filter_by(user_id=user_id).count()
    leads = Lead.query.filter_by(user_id=user_id).count()
    new_leads_30 = Lead.query.filter(
        Lead.user_id == user_id,
        Lead.created_at >= datetime.utcnow() - timedelta(days=30),
    ).count()
    automations_active = Automation.query.filter_by(user_id=user_id, enabled=True).count()

    if overdue > 0:
        suggestions.append({
            'priority': 'high',
            'icon': 'alert-triangle',
            'color': 'red',
            'title': f'Cobrança automática para {overdue} fatura(s) vencida(s)',
            'description': 'WhatsApp + email automático quando fatura passa do prazo. Recupera receita sem esforço manual.',
            'template_id': 'overdue_alert',
        })

    if pending >= 3:
        suggestions.append({
            'priority': 'medium',
            'icon': 'clock',
            'color': 'amber',
            'title': f'Lembrete de vencimento para {pending} fatura(s) pendente(s)',
            'description': 'Avise seus clientes 3 dias antes do vencimento para reduzir inadimplência.',
            'template_id': 'invoice_reminder',
        })

    if contacts > 5 and automations_active == 0:
        suggestions.append({
            'priority': 'medium',
            'icon': 'mail',
            'color': 'blue',
            'title': 'Boas-vindas automáticas para novos contatos',
            'description': f'Você tem {contacts} contatos. Configure email de boas-vindas para causar primeira impressão profissional.',
            'template_id': 'welcome_email',
        })

    if new_leads_30 >= 3:
        suggestions.append({
            'priority': 'medium',
            'icon': 'target',
            'color': 'purple',
            'title': 'Follow-up automático de leads frios',
            'description': f'{new_leads_30} novos leads nos últimos 30 dias. Reengaje os que não responderam em 3 dias.',
            'template_id': 'lead_followup',
        })

    if leads >= 1:
        suggestions.append({
            'priority': 'low',
            'icon': 'check-circle',
            'color': 'green',
            'title': 'Comemorar vendas fechadas no Slack',
            'description': 'Aumenta moral do time e celebra cada lead ganho automaticamente.',
            'template_id': 'won_lead_celebration',
        })

    suggestions.append({
        'priority': 'low',
        'icon': 'bar-chart-3',
        'color': 'cyan',
        'title': 'Relatório executivo semanal',
        'description': 'Receba toda segunda-feira um resumo completo da operação.',
        'template_id': 'weekly_report',
    })

    return suggestions


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers internos
# ═══════════════════════════════════════════════════════════════════════════════

def _log(user_id: int, automation_id: int | None, status: str,
         trigger: str, action: str, message: str, duration_ms: int = 0,
         payload: dict | None = None):
    log = AutomationLog(
        user_id=user_id,
        automation_id=automation_id,
        status=status,
        trigger=trigger,
        action=action,
        message=message[:400] if message else '',
        duration_ms=duration_ms,
        payload=json.dumps(payload or {}),
    )
    db.session.add(log)
    db.session.commit()


def trigger_event(user_id: int, event: str, payload: dict | None = None) -> int:
    """
    Dispara um evento em runtime. Cada automação ativa com esse trigger é
    EXECUTADA DE VERDADE (chama integrações reais via action_executor).

    Retorna número de automações executadas com sucesso.
    """
    autos = Automation.query.filter_by(user_id=user_id, trigger=event, enabled=True).all()
    fired = 0
    for a in autos:
        ok, _ = simulate_run(user_id, a.id, payload)
        if ok:
            fired += 1
    return fired
