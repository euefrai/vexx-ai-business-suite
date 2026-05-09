"""
VEXX AI — Action Executor
Executa ações reais via APIs externas. Chamado pelo automation_service ao
disparar uma automação. Nunca lança exceção: retorna sempre (ok, message).

Cada ação usa as credenciais salvas (cifradas) na integração do usuário.
Se o usuário não tem a integração necessária, a execução falha graciosamente
com mensagem clara que vai parar nos logs.
"""

import json
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from services.integrations_service import get_credentials
from database.models import create_notification


# ═══════════════════════════════════════════════════════════════════════════════
# Variable substitution (Jinja-lite — só {{path.to.value}})
# ═══════════════════════════════════════════════════════════════════════════════

def render(template: str, context: dict) -> str:
    """{{contact.name}}, {{invoice.amount}}, {{lead.title}}..."""
    if not template:
        return ''
    out = template
    import re
    for match in re.finditer(r'\{\{\s*([\w\.]+)\s*\}\}', template):
        full, path = match.group(0), match.group(1)
        value = context
        for part in path.split('.'):
            value = value.get(part) if isinstance(value, dict) else None
            if value is None:
                break
        out = out.replace(full, str(value) if value is not None else '')
    return out


# ═══════════════════════════════════════════════════════════════════════════════
# Public dispatcher
# ═══════════════════════════════════════════════════════════════════════════════

def execute(user_id: int, action_id: str, params: dict, context: dict | None = None) -> tuple[bool, str]:
    """
    Executa uma ação. `params` vem da config do automation step.
    `context` traz dados do trigger (contact, lead, invoice, transaction...).
    """
    ctx = context or {}
    handler = _ACTIONS.get(action_id)
    if not handler:
        return False, f'Ação desconhecida: {action_id}'

    try:
        return handler(user_id, params, ctx)
    except requests.exceptions.RequestException as e:
        return False, f'Falha de rede: {str(e)[:200]}'
    except Exception as e:
        return False, f'Erro inesperado: {str(e)[:200]}'


# ═══════════════════════════════════════════════════════════════════════════════
# Handlers
# ═══════════════════════════════════════════════════════════════════════════════

def _split_emails(value: str) -> list[str]:
    """Aceita string com vírgulas, ponto-e-vírgulas ou quebras de linha."""
    if not value:
        return []
    import re
    parts = re.split(r'[,;\n]+', str(value))
    return [p.strip() for p in parts if p.strip() and '@' in p]


def _send_email(user_id, params, ctx):
    """
    Envia email via SMTP ou Gmail. Suporta:
      - Múltiplos destinatários separados por vírgula no campo `to`
      - CC e BCC (campos opcionais)
      - Variáveis {{...}} em qualquer campo
      - HTML (detectado automaticamente se houver `<` no body)
    """
    to_raw  = render(params.get('to', ''), ctx) or ctx.get('contact', {}).get('email', '')
    cc_raw  = render(params.get('cc', ''), ctx)
    bcc_raw = render(params.get('bcc', ''), ctx)
    subject = render(params.get('subject', '[Sem assunto]'), ctx)
    body    = render(params.get('body', ''), ctx)

    to_list  = _split_emails(to_raw)
    cc_list  = _split_emails(cc_raw)
    bcc_list = _split_emails(bcc_raw)

    if not to_list:
        return False, 'Nenhum email de destinatário válido.'

    smtp_creds = get_credentials(user_id, 'smtp')
    if smtp_creds:
        return _smtp_send(smtp_creds, to_list, cc_list, bcc_list, subject, body)

    gmail_creds = get_credentials(user_id, 'gmail')
    if gmail_creds:
        return _gmail_send(gmail_creds, to_list, cc_list, bcc_list, subject, body, _user_id=user_id)

    return False, 'Nenhuma integração de email (SMTP/Gmail) conectada.'


def _smtp_send(creds, to_list, cc_list, bcc_list, subject, body):
    host = creds.get('host')
    port = int(creds.get('port', 587))
    user = creds.get('username')
    pw   = creds.get('password')
    use_tls = creds.get('use_tls', True)

    msg = MIMEMultipart('alternative')
    msg['From'] = user
    msg['To']      = ', '.join(to_list)
    if cc_list:
        msg['Cc'] = ', '.join(cc_list)
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html' if '<' in body else 'plain'))

    all_recipients = to_list + cc_list + bcc_list  # BCC entra na lista mas NÃO no header

    with smtplib.SMTP(host, port, timeout=15) as server:
        if use_tls:
            server.starttls()
        server.login(user, pw)
        server.sendmail(user, all_recipients, msg.as_string())

    summary = f'Email enviado para {len(to_list)} destinatário(s)'
    if cc_list:  summary += f', {len(cc_list)} em cópia'
    if bcc_list: summary += f', {len(bcc_list)} em cópia oculta'
    return True, summary


def _gmail_send(creds, to_list, cc_list, bcc_list, subject, body, _user_id=None, _retried=False):
    """Gmail API via REST com OAuth access_token. Auto-refresh on 401."""
    import base64
    raw = MIMEText(body, 'html' if '<' in body else 'plain')
    raw['To']      = ', '.join(to_list)
    if cc_list:
        raw['Cc']  = ', '.join(cc_list)
    if bcc_list:
        raw['Bcc'] = ', '.join(bcc_list)
    raw['From']    = creds.get('from_email', '')
    raw['Subject'] = subject
    encoded = base64.urlsafe_b64encode(raw.as_bytes()).decode()

    r = requests.post(
        'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
        headers={'Authorization': f'Bearer {creds["access_token"]}', 'Content-Type': 'application/json'},
        json={'raw': encoded},
        timeout=15,
    )

    # Auto-refresh: se 401 e temos refresh_token, renova e tenta de novo
    if r.status_code == 401 and not _retried and _user_id:
        from services.oauth_service import refresh_token as do_refresh
        refreshed = do_refresh(_user_id, 'gmail')
        if refreshed:
            fresh_creds = get_credentials(_user_id, 'gmail')
            if fresh_creds:
                return _gmail_send(fresh_creds, to_list, cc_list, bcc_list, subject, body,
                                   _user_id=_user_id, _retried=True)
        return False, 'Token Gmail expirado e não foi possível renovar. Reconecte o Gmail em Integrações.'

    if r.status_code >= 400:
        return False, f'Gmail erro {r.status_code}: {r.text[:200]}'

    summary = f'Gmail: enviado para {len(to_list)} destinatário(s)'
    if cc_list:  summary += f', {len(cc_list)} em cópia'
    if bcc_list: summary += f', {len(bcc_list)} em cópia oculta'
    return True, summary


def _send_whatsapp(user_id, params, ctx):
    """WhatsApp Cloud API (Meta). Usa integration 'whatsapp'."""
    creds = get_credentials(user_id, 'whatsapp')
    if not creds:
        return False, 'WhatsApp não conectado em Integrações.'

    to = render(params.get('to', ''), ctx) or ctx.get('contact', {}).get('phone')
    text = render(params.get('text', params.get('message', '')), ctx)
    if not to or not text:
        return False, 'Telefone e mensagem são obrigatórios.'

    # Normaliza número: só dígitos, sem +
    to_clean = ''.join(filter(str.isdigit, str(to)))

    r = requests.post(
        f'https://graph.facebook.com/v18.0/{creds["phone_number_id"]}/messages',
        headers={'Authorization': f'Bearer {creds["access_token"]}', 'Content-Type': 'application/json'},
        json={
            'messaging_product': 'whatsapp',
            'to': to_clean,
            'type': 'text',
            'text': {'body': text},
        },
        timeout=15,
    )
    if r.status_code >= 400:
        return False, f'WhatsApp erro {r.status_code}: {r.text[:200]}'
    return True, f'WhatsApp enviado para +{to_clean}'


def _send_telegram(user_id, params, ctx):
    creds = get_credentials(user_id, 'telegram')
    if not creds:
        return False, 'Telegram não conectado.'

    chat_id = params.get('chat_id') or creds.get('chat_id')
    text = render(params.get('text', params.get('message', '')), ctx)
    if not chat_id or not text:
        return False, 'chat_id e mensagem são obrigatórios.'

    r = requests.post(
        f'https://api.telegram.org/bot{creds["bot_token"]}/sendMessage',
        json={'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'},
        timeout=15,
    )
    if r.status_code >= 400:
        return False, f'Telegram erro {r.status_code}: {r.text[:200]}'
    return True, f'Telegram enviado'


def _send_slack(user_id, params, ctx):
    creds = get_credentials(user_id, 'slack')
    if not creds:
        return False, 'Slack não conectado.'

    text = render(params.get('text', params.get('message', '')), ctx)
    if not text:
        return False, 'Mensagem vazia.'

    r = requests.post(creds['webhook_url'], json={'text': text}, timeout=15)
    if r.status_code >= 400:
        return False, f'Slack erro {r.status_code}'
    return True, 'Slack notificado'


def _send_discord(user_id, params, ctx):
    creds = get_credentials(user_id, 'discord')
    if not creds:
        return False, 'Discord não conectado.'

    text = render(params.get('text', params.get('message', '')), ctx)
    if not text:
        return False, 'Mensagem vazia.'

    r = requests.post(creds['webhook_url'], json={'content': text}, timeout=15)
    if r.status_code >= 400:
        return False, f'Discord erro {r.status_code}'
    return True, 'Discord notificado'


def _call_webhook(user_id, params, ctx):
    creds = get_credentials(user_id, 'webhook') or {}
    url = params.get('url') or creds.get('url')
    method = (params.get('method') or creds.get('method') or 'POST').upper()
    headers_raw = params.get('headers') or creds.get('headers') or '{}'
    body = params.get('body', ctx)

    if not url:
        return False, 'URL do webhook não informada.'

    try:
        headers = json.loads(headers_raw) if isinstance(headers_raw, str) else headers_raw
    except Exception:
        headers = {}

    rendered = json.loads(render(json.dumps(body), ctx)) if isinstance(body, dict) else body
    r = requests.request(method, url, headers=headers, json=rendered, timeout=15)
    if r.status_code >= 400:
        return False, f'Webhook respondeu {r.status_code}'
    return True, f'Webhook chamado ({method} → {r.status_code})'


def _notify_team(user_id, params, ctx):
    """Cria Notification interna que aparece no sino do topbar."""
    title = render(params.get('title', 'Alerta da automação'), ctx)
    desc  = render(params.get('description', ''), ctx)
    create_notification(user_id, params.get('type', 'info'), title, desc, params.get('link', ''))
    return True, f'Equipe notificada: "{title}"'


def _create_task(user_id, params, ctx):
    """Stub — em produção criaria registro em tabela tasks."""
    title = render(params.get('title', 'Tarefa automática'), ctx)
    create_notification(user_id, 'info', f'📋 Nova tarefa: {title}',
                        render(params.get('description', ''), ctx))
    return True, f'Tarefa criada: "{title}"'


def _update_lead_stage(user_id, params, ctx):
    """Atualiza estágio de um lead via contexto."""
    from database.db import db
    from database.models import Lead
    lead_id = params.get('lead_id') or ctx.get('lead', {}).get('id')
    new_stage = params.get('stage', '')
    if not lead_id or not new_stage:
        return False, 'lead_id e stage obrigatórios.'
    lead = Lead.query.filter_by(id=lead_id, user_id=user_id).first()
    if not lead:
        return False, 'Lead não encontrado.'
    lead.stage = new_stage
    db.session.commit()
    return True, f'Lead movido para {new_stage}'


def _create_invoice(user_id, params, ctx):
    from services.finance_service import create_invoice
    amount = params.get('amount') or ctx.get('lead', {}).get('value')
    if not amount:
        return False, 'amount obrigatório.'
    ok, msg, _ = create_invoice(user_id, {
        'amount': amount,
        'description': render(params.get('description', 'Cobrança automática'), ctx),
        'contact_id': params.get('contact_id') or ctx.get('contact', {}).get('id'),
    })
    return ok, msg


def _ai_insight(user_id, params, ctx):
    """Gera insight com IA: usa provider externo se houver API key, senão fallback."""
    from database.models import User
    import services.ai_service as ai_svc
    user = User.query.get(user_id)
    if not user:
        return False, 'Usuário não encontrado.'

    prompt = render(params.get('prompt', 'Gere um insight executivo do meu negócio'), ctx)
    intents = ai_svc.detect_intents(prompt)
    system_prompt = ai_svc.build_system_prompt(user, intents)

    provider, api_key = ai_svc.get_user_api_key(user_id)
    if api_key:
        try:
            messages = [{'role': 'user', 'content': prompt}]
            reply = ai_svc._call_provider(provider, api_key, messages, system_prompt)
        except Exception:
            reply = ai_svc._smart_fallback(prompt, user, intents)
    else:
        reply = ai_svc._smart_fallback(prompt, user, intents)

    create_notification(user_id, 'ai', '🤖 Insight da IA', reply[:300], '/ai-assistant')
    return True, 'Insight gerado e notificado'


def _generate_report(user_id, params, ctx):
    """Gera PDF executivo real e cria notificação com link de download."""
    from services.report_service import generate_executive_pdf
    try:
        _, filename = generate_executive_pdf(user_id)
        create_notification(
            user_id, 'success', '📊 Relatório executivo pronto',
            f'PDF gerado: {filename}',
            f'/api/reports/download/{filename}',
        )
        return True, f'PDF gerado: {filename}'
    except Exception as e:
        return False, f'Erro ao gerar PDF: {str(e)[:200]}'


def _append_sheet(user_id, params, ctx):
    creds = get_credentials(user_id, 'google_sheets')
    if not creds:
        return False, 'Google Sheets não conectado.'

    sheet_id = params.get('spreadsheet_id') or creds.get('spreadsheet_id')
    range_ = params.get('range', 'Sheet1!A:Z')
    values = params.get('values', list(ctx.values()) if isinstance(ctx, dict) else [])

    r = requests.post(
        f'https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{range_}:append?valueInputOption=USER_ENTERED',
        headers={'Authorization': f'Bearer {creds["access_token"]}', 'Content-Type': 'application/json'},
        json={'values': [values]},
        timeout=15,
    )
    if r.status_code >= 400:
        return False, f'Sheets erro {r.status_code}'
    return True, 'Linha adicionada à planilha'


def _sync_bank(user_id, params, ctx):
    """Sync REAL via Pluggy. Requer item_id (ou usa o salvo na config)."""
    from services.pluggy_service import sync_transactions, list_items
    creds = get_credentials(user_id, 'pluggy')
    if not creds:
        return False, 'Pluggy não conectado em Integrações.'

    item_id = params.get('item_id') or creds.get('default_item_id')
    if not item_id:
        # Tenta usar o primeiro item disponível
        items = list_items(user_id)
        if not items:
            return False, 'Nenhum banco conectado via Pluggy. Use Pluggy Connect primeiro.'
        item_id = items[0]['id']

    days = int(params.get('days', 30))
    ok, msg, count = sync_transactions(user_id, item_id, days)
    return ok, msg


# ═══════════════════════════════════════════════════════════════════════════════
# Action registry
# ═══════════════════════════════════════════════════════════════════════════════

_ACTIONS = {
    'send_email':           _send_email,
    'send_whatsapp':        _send_whatsapp,
    'send_telegram':        _send_telegram,
    'send_slack':           _send_slack,
    'send_discord':         _send_discord,
    'call_webhook':         _call_webhook,
    'notify_team':          _notify_team,
    'create_task':          _create_task,
    'update_lead_stage':    _update_lead_stage,
    'create_invoice':       _create_invoice,
    'ai_insight':           _ai_insight,
    'generate_report':      _generate_report,
    'append_sheet':         _append_sheet,
    'sync_bank':            _sync_bank,
}
