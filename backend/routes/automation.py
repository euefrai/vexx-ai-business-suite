"""
VEXX AI — Automation routes
Workflows + Integrations + Logs + Templates + IA Suggestions + Webhooks.
"""

from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user
from services.automation_service import (
    list_automations, create_automation, update_automation, toggle_automation,
    delete_automation, simulate_run, get_automation_stats,
    list_logs, list_templates, create_from_template,
    get_ai_suggestions, trigger_event, TRIGGERS, ACTIONS,
)
from services.integrations_service import (
    list_providers, get_provider, list_user_integrations,
    connect_integration, disconnect_integration, test_integration,
    CATEGORIES,
)
from utils.permissions import check_limit
from database.db import csrf

automation_bp = Blueprint('automation', __name__)


# ─── Page ────────────────────────────────────────────────────────────────────
@automation_bp.route('/automation')
@login_required
def automation_page():
    return render_template('automation.html')


# ═══════════════════════════════════════════════════════════════════════════════
# WORKFLOWS / AUTOMAÇÕES
# ═══════════════════════════════════════════════════════════════════════════════

@automation_bp.route('/api/automation/stats')
@login_required
def api_stats():
    return jsonify({'success': True, 'data': get_automation_stats(current_user.id)})


@automation_bp.route('/api/automation/list')
@login_required
def api_list():
    return jsonify({'success': True, 'data': list_automations(current_user.id)})


@automation_bp.route('/api/automation', methods=['POST'])
@login_required
def api_create():
    allowed, msg = check_limit(current_user, 'automations')
    if not allowed:
        return jsonify({'success': False, 'error': msg}), 403

    data = request.get_json() or {}
    ok, msg, auto = create_automation(current_user.id, data)
    return jsonify({'success': ok, 'message': msg, 'data': auto}), (201 if ok else 400)


@automation_bp.route('/api/automation/<int:auto_id>', methods=['PUT', 'PATCH'])
@login_required
def api_update(auto_id):
    data = request.get_json() or {}
    ok, msg = update_automation(current_user.id, auto_id, data)
    return jsonify({'success': ok, 'message': msg}), (200 if ok else 404)


@automation_bp.route('/api/automation/<int:auto_id>/toggle', methods=['PATCH'])
@login_required
def api_toggle(auto_id):
    ok, msg, enabled = toggle_automation(current_user.id, auto_id)
    return jsonify({'success': ok, 'message': msg, 'enabled': enabled}), (200 if ok else 404)


@automation_bp.route('/api/automation/<int:auto_id>/run', methods=['POST'])
@login_required
def api_run(auto_id):
    ok, msg = simulate_run(current_user.id, auto_id)
    return jsonify({'success': ok, 'message': msg}), (200 if ok else 404)


@automation_bp.route('/api/automation/<int:auto_id>', methods=['DELETE'])
@login_required
def api_delete(auto_id):
    ok, msg = delete_automation(current_user.id, auto_id)
    return jsonify({'success': ok, 'message': msg}), (200 if ok else 404)


# ═══════════════════════════════════════════════════════════════════════════════
# TRIGGERS / ACTIONS catálogo
# ═══════════════════════════════════════════════════════════════════════════════

@automation_bp.route('/api/automation/catalog')
@login_required
def api_catalog():
    return jsonify({'success': True, 'data': {'triggers': TRIGGERS, 'actions': ACTIONS}})


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATIONS HUB
# ═══════════════════════════════════════════════════════════════════════════════

@automation_bp.route('/api/automation/integrations/providers')
@login_required
def api_providers():
    return jsonify({'success': True, 'data': list_providers(), 'categories': CATEGORIES})


@automation_bp.route('/api/automation/integrations/providers/<provider_id>')
@login_required
def api_provider_detail(provider_id):
    p = get_provider(provider_id)
    if not p:
        return jsonify({'success': False, 'error': 'Provider não encontrado.'}), 404
    return jsonify({'success': True, 'data': p})


@automation_bp.route('/api/automation/integrations')
@login_required
def api_integrations():
    return jsonify({'success': True, 'data': list_user_integrations(current_user.id)})


@automation_bp.route('/api/automation/integrations/connect', methods=['POST'])
@login_required
def api_connect():
    data = request.get_json() or {}
    provider = data.get('provider')
    if not provider:
        return jsonify({'success': False, 'error': 'provider é obrigatório.'}), 400

    ok, msg, integ = connect_integration(
        current_user.id, provider,
        name=data.get('name', ''),
        credentials=data.get('credentials', {}),
        config=data.get('config', {}),
    )
    return jsonify({'success': ok, 'message': msg, 'data': integ}), (200 if ok else 400)


@automation_bp.route('/api/automation/integrations/<int:integ_id>', methods=['DELETE'])
@login_required
def api_disconnect(integ_id):
    ok, msg = disconnect_integration(current_user.id, integ_id)
    return jsonify({'success': ok, 'message': msg}), (200 if ok else 404)


@automation_bp.route('/api/automation/integrations/<int:integ_id>/test', methods=['POST'])
@login_required
def api_test_integration(integ_id):
    ok, msg = test_integration(current_user.id, integ_id)
    return jsonify({'success': ok, 'message': msg}), (200 if ok else 404)


# ═══════════════════════════════════════════════════════════════════════════════
# LOGS
# ═══════════════════════════════════════════════════════════════════════════════

@automation_bp.route('/api/automation/logs')
@login_required
def api_logs():
    status = request.args.get('status', '')
    limit = int(request.args.get('limit', 100))
    return jsonify({'success': True, 'data': list_logs(current_user.id, limit, status)})


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATES + IA SUGGESTIONS
# ═══════════════════════════════════════════════════════════════════════════════

@automation_bp.route('/api/automation/templates')
@login_required
def api_templates():
    return jsonify({'success': True, 'data': list_templates()})


@automation_bp.route('/api/automation/templates/<template_id>/use', methods=['POST'])
@login_required
def api_use_template(template_id):
    allowed, msg = check_limit(current_user, 'automations')
    if not allowed:
        return jsonify({'success': False, 'error': msg}), 403

    ok, msg, auto = create_from_template(current_user.id, template_id)
    return jsonify({'success': ok, 'message': msg, 'data': auto}), (201 if ok else 400)


@automation_bp.route('/api/automation/suggestions')
@login_required
def api_suggestions():
    return jsonify({'success': True, 'data': get_ai_suggestions(current_user.id)})


# ═══════════════════════════════════════════════════════════════════════════════
# WEBHOOKS — endpoint público para receber eventos externos
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
# PLUGGY (Open Finance Brasil)
# ═══════════════════════════════════════════════════════════════════════════════

@automation_bp.route('/api/automation/pluggy/connect-token', methods=['POST'])
@login_required
def api_pluggy_token():
    from services.pluggy_service import create_connect_token
    ok, msg, data = create_connect_token(current_user.id)
    return jsonify({'success': ok, 'message': msg, 'data': data}), (200 if ok else 400)


@automation_bp.route('/api/automation/pluggy/items')
@login_required
def api_pluggy_items():
    from services.pluggy_service import list_items
    return jsonify({'success': True, 'data': list_items(current_user.id)})


@automation_bp.route('/api/automation/pluggy/sync/<item_id>', methods=['POST'])
@login_required
def api_pluggy_sync(item_id):
    from services.pluggy_service import sync_transactions
    ok, msg, count = sync_transactions(current_user.id, item_id)
    return jsonify({'success': ok, 'message': msg, 'imported': count}), (200 if ok else 400)


@automation_bp.route('/webhooks/<int:user_id>/<event>', methods=['POST', 'GET'])
@csrf.exempt
def webhook_receiver(user_id, event):
    """
    Endpoint público que dispara automações com trigger='incoming_webhook'
    ou com trigger igual ao `event` recebido na URL.
    """
    payload = request.get_json(silent=True) or dict(request.args) or {}
    fired = trigger_event(user_id, event, payload)
    fired += trigger_event(user_id, 'incoming_webhook', {'event': event, **payload})
    return jsonify({
        'success': True,
        'event': event,
        'automations_fired': fired,
        'message': f'{fired} automação(ões) disparada(s).',
    })


@automation_bp.route('/webhooks/stripe/<int:user_id>', methods=['POST'])
@csrf.exempt
def stripe_webhook(user_id):
    """
    Recebe eventos Stripe e valida assinatura HMAC com webhook_secret salvo.
    https://stripe.com/docs/webhooks/signatures
    """
    import hmac
    import hashlib
    import time
    from services.integrations_service import get_credentials

    creds = get_credentials(user_id, 'stripe')
    if not creds or not creds.get('webhook_secret'):
        return jsonify({'error': 'Stripe não configurado para este usuário.'}), 400

    sig_header = request.headers.get('Stripe-Signature', '')
    payload_bytes = request.get_data()

    # Parse "t=...,v1=..."
    parts = dict(p.split('=', 1) for p in sig_header.split(',') if '=' in p)
    timestamp = parts.get('t', '')
    received_sig = parts.get('v1', '')

    if not timestamp or not received_sig:
        return jsonify({'error': 'Assinatura ausente.'}), 400

    # Tolerância de 5 minutos
    try:
        if abs(time.time() - int(timestamp)) > 300:
            return jsonify({'error': 'Timestamp expirado.'}), 400
    except ValueError:
        return jsonify({'error': 'Timestamp inválido.'}), 400

    signed = f'{timestamp}.{payload_bytes.decode()}'
    expected = hmac.HMAC(creds['webhook_secret'].encode(), signed.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, received_sig):
        return jsonify({'error': 'Assinatura inválida.'}), 401

    event = request.get_json(silent=True) or {}
    event_type = event.get('type', '')

    # Mapeia eventos Stripe → triggers VEXX
    mapping = {
        'payment_intent.succeeded':    'payment_received',
        'invoice.paid':                'payment_received',
        'invoice.payment_failed':      'invoice_overdue',
        'customer.subscription.created': 'payment_received',
        'customer.subscription.deleted': 'subscription_canceled',
    }
    vexx_event = mapping.get(event_type, 'incoming_webhook')

    fired = trigger_event(user_id, vexx_event, {
        'stripe_event': event_type,
        'amount': (event.get('data', {}).get('object', {}).get('amount') or 0) / 100,
        'object': event.get('data', {}).get('object', {}),
    })
    return jsonify({'received': True, 'fired': fired})
