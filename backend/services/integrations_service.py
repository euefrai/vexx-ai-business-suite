"""
VEXX AI — Integrations Hub
Catálogo de provedores e gerenciamento de credenciais criptografadas (Fernet).

Cada provedor declara:
  - id, name, category, icon (lucide), description
  - auth_type: api_key | oauth | smtp | webhook | basic
  - fields: lista de campos do form (key, label, type, placeholder, required)
  - actions: lista de ações disponíveis (para o workflow builder)
  - triggers: lista de gatilhos disponíveis
"""

import json
from datetime import datetime
from database.db import db
from database.models import Integration
from utils.security import encrypt_api_key, decrypt_api_key


# ── Catálogo de providers ────────────────────────────────────────────────────
PROVIDERS = {
    # ─ Comunicação ───────────────────────────────────────────
    'gmail': {
        'name': 'Gmail',
        'category': 'communication',
        'icon': 'mail',
        'color': '#EA4335',
        'auth_type': 'oauth',
        'description': 'Envie emails, leia caixa de entrada e dispare automações.',
        'fields': [
            {'key': 'access_token', 'label': 'Access Token (OAuth)', 'type': 'password', 'required': True,
             'help': 'Cole o token gerado no Google Cloud Console.'},
            {'key': 'from_email', 'label': 'Email remetente', 'type': 'email', 'required': True},
        ],
        'actions': ['send_email', 'reply_email', 'add_label'],
        'triggers': ['new_email', 'starred_email'],
    },
    'outlook': {
        'name': 'Outlook / Microsoft 365',
        'category': 'communication',
        'icon': 'mail',
        'color': '#0078D4',
        'auth_type': 'oauth',
        'description': 'Microsoft 365 / Exchange — emails, calendário e contatos.',
        'fields': [
            {'key': 'access_token', 'label': 'Access Token', 'type': 'password', 'required': True},
            {'key': 'tenant_id', 'label': 'Tenant ID', 'type': 'text', 'required': False},
        ],
        'actions': ['send_email', 'create_event'],
        'triggers': ['new_email', 'new_event'],
    },
    'smtp': {
        'name': 'SMTP customizado',
        'category': 'communication',
        'icon': 'send',
        'color': '#6B7280',
        'auth_type': 'smtp',
        'description': 'Servidor SMTP próprio (qualquer provedor).',
        'fields': [
            {'key': 'host', 'label': 'Host', 'type': 'text', 'placeholder': 'smtp.exemplo.com', 'required': True},
            {'key': 'port', 'label': 'Porta', 'type': 'number', 'placeholder': '587', 'required': True},
            {'key': 'username', 'label': 'Usuário', 'type': 'text', 'required': True},
            {'key': 'password', 'label': 'Senha', 'type': 'password', 'required': True},
            {'key': 'use_tls', 'label': 'TLS', 'type': 'checkbox'},
        ],
        'actions': ['send_email'],
        'triggers': [],
    },
    'whatsapp': {
        'name': 'WhatsApp Business',
        'category': 'messaging',
        'icon': 'message-circle',
        'color': '#25D366',
        'auth_type': 'api_key',
        'description': 'Envie mensagens, templates e atendimento automatizado via WhatsApp Cloud API.',
        'fields': [
            {'key': 'phone_number_id', 'label': 'Phone Number ID', 'type': 'text', 'required': True},
            {'key': 'access_token',    'label': 'Access Token (Meta)', 'type': 'password', 'required': True},
            {'key': 'business_id',     'label': 'WhatsApp Business Account ID', 'type': 'text'},
        ],
        'actions': ['send_message', 'send_template', 'send_image'],
        'triggers': ['new_message', 'message_received'],
    },
    'telegram': {
        'name': 'Telegram',
        'category': 'messaging',
        'icon': 'send',
        'color': '#26A5E4',
        'auth_type': 'api_key',
        'description': 'Bots e canais para notificações instantâneas.',
        'fields': [
            {'key': 'bot_token', 'label': 'Bot Token', 'type': 'password', 'required': True,
             'help': 'Crie um bot via @BotFather'},
            {'key': 'chat_id',   'label': 'Chat ID padrão', 'type': 'text'},
        ],
        'actions': ['send_message', 'send_photo'],
        'triggers': ['new_message'],
    },
    'slack': {
        'name': 'Slack',
        'category': 'messaging',
        'icon': 'hash',
        'color': '#4A154B',
        'auth_type': 'api_key',
        'description': 'Notificações em canais e DMs.',
        'fields': [
            {'key': 'webhook_url', 'label': 'Incoming Webhook URL', 'type': 'text', 'required': True},
        ],
        'actions': ['post_message'],
        'triggers': ['slash_command'],
    },
    'discord': {
        'name': 'Discord',
        'category': 'messaging',
        'icon': 'message-square',
        'color': '#5865F2',
        'auth_type': 'webhook',
        'description': 'Webhooks para canais Discord.',
        'fields': [
            {'key': 'webhook_url', 'label': 'Webhook URL', 'type': 'text', 'required': True},
        ],
        'actions': ['post_message', 'post_embed'],
        'triggers': [],
    },

    # ─ Pagamentos ────────────────────────────────────────────
    'stripe': {
        'name': 'Stripe',
        'category': 'payments',
        'icon': 'credit-card',
        'color': '#635BFF',
        'auth_type': 'api_key',
        'description': 'Cobranças, assinaturas e webhooks de pagamento.',
        'fields': [
            {'key': 'secret_key',     'label': 'Secret Key',  'type': 'password', 'placeholder': 'sk_live_...', 'required': True},
            {'key': 'webhook_secret', 'label': 'Webhook Secret', 'type': 'password'},
        ],
        'actions': ['create_charge', 'create_subscription', 'send_invoice'],
        'triggers': ['payment_received', 'subscription_canceled', 'invoice_paid'],
    },
    'mercadopago': {
        'name': 'Mercado Pago',
        'category': 'payments',
        'icon': 'wallet',
        'color': '#009EE3',
        'auth_type': 'api_key',
        'description': 'Pagamentos PIX, cartão e boleto via Mercado Pago.',
        'fields': [
            {'key': 'access_token', 'label': 'Access Token', 'type': 'password', 'required': True},
            {'key': 'public_key',   'label': 'Public Key',   'type': 'text'},
        ],
        'actions': ['create_payment', 'create_pix'],
        'triggers': ['payment_approved', 'payment_canceled'],
    },
    'paypal': {
        'name': 'PayPal',
        'category': 'payments',
        'icon': 'dollar-sign',
        'color': '#003087',
        'auth_type': 'api_key',
        'description': 'Pagamentos internacionais via PayPal.',
        'fields': [
            {'key': 'client_id',     'label': 'Client ID',     'type': 'text', 'required': True},
            {'key': 'client_secret', 'label': 'Client Secret', 'type': 'password', 'required': True},
        ],
        'actions': ['create_invoice', 'create_payment'],
        'triggers': ['payment_completed'],
    },

    # ─ Bancos / Open Finance ─────────────────────────────────
    'open_finance': {
        'name': 'Open Finance Brasil',
        'category': 'banking',
        'icon': 'landmark',
        'color': '#10B981',
        'auth_type': 'oauth',
        'description': 'Sincronização de saldo, extratos e PIX dos principais bancos brasileiros.',
        'fields': [
            {'key': 'access_token',   'label': 'Access Token (Open Finance)', 'type': 'password', 'required': True},
            {'key': 'institution_id', 'label': 'Banco (ISPB)', 'type': 'text', 'placeholder': '00000000'},
        ],
        'actions': ['sync_transactions', 'create_pix'],
        'triggers': ['new_transaction', 'low_balance'],
    },
    'pluggy': {
        'name': 'Pluggy',
        'category': 'banking',
        'icon': 'banknote',
        'color': '#7B61FF',
        'auth_type': 'api_key',
        'description': 'Conector unificado para 30+ bancos brasileiros.',
        'fields': [
            {'key': 'client_id',     'label': 'Client ID',     'type': 'text', 'required': True},
            {'key': 'client_secret', 'label': 'Client Secret', 'type': 'password', 'required': True},
        ],
        'actions': ['sync_accounts', 'fetch_transactions'],
        'triggers': ['new_transaction'],
    },

    # ─ Produtividade ─────────────────────────────────────────
    'google_sheets': {
        'name': 'Google Sheets',
        'category': 'productivity',
        'icon': 'table',
        'color': '#0F9D58',
        'auth_type': 'oauth',
        'description': 'Adicione/leia linhas em planilhas automaticamente.',
        'fields': [
            {'key': 'access_token', 'label': 'Access Token', 'type': 'password', 'required': True},
            {'key': 'spreadsheet_id', 'label': 'Spreadsheet ID padrão', 'type': 'text'},
        ],
        'actions': ['append_row', 'update_cell', 'read_range'],
        'triggers': ['new_row'],
    },
    'google_calendar': {
        'name': 'Google Calendar',
        'category': 'productivity',
        'icon': 'calendar',
        'color': '#4285F4',
        'auth_type': 'oauth',
        'description': 'Crie e atualize eventos.',
        'fields': [
            {'key': 'access_token', 'label': 'Access Token', 'type': 'password', 'required': True},
        ],
        'actions': ['create_event', 'update_event'],
        'triggers': ['new_event'],
    },
    'notion': {
        'name': 'Notion',
        'category': 'productivity',
        'icon': 'book-open',
        'color': '#000000',
        'auth_type': 'api_key',
        'description': 'Páginas, databases e wiki da empresa.',
        'fields': [
            {'key': 'integration_token', 'label': 'Integration Token', 'type': 'password', 'required': True},
        ],
        'actions': ['create_page', 'add_db_row'],
        'triggers': [],
    },
    'trello': {
        'name': 'Trello',
        'category': 'productivity',
        'icon': 'kanban',
        'color': '#0079BF',
        'auth_type': 'api_key',
        'description': 'Quadros e cards Trello.',
        'fields': [
            {'key': 'api_key', 'label': 'API Key', 'type': 'text', 'required': True},
            {'key': 'token',   'label': 'Token',   'type': 'password', 'required': True},
        ],
        'actions': ['create_card', 'move_card'],
        'triggers': [],
    },

    # ─ E-commerce ────────────────────────────────────────────
    'shopify': {
        'name': 'Shopify',
        'category': 'ecommerce',
        'icon': 'shopping-bag',
        'color': '#96BF48',
        'auth_type': 'api_key',
        'description': 'Pedidos, produtos e clientes Shopify.',
        'fields': [
            {'key': 'shop_domain',  'label': 'Shop domain', 'type': 'text', 'placeholder': 'minha-loja.myshopify.com', 'required': True},
            {'key': 'access_token', 'label': 'Admin Access Token', 'type': 'password', 'required': True},
        ],
        'actions': ['create_order', 'update_product'],
        'triggers': ['new_order', 'order_paid'],
    },
    'woocommerce': {
        'name': 'WooCommerce',
        'category': 'ecommerce',
        'icon': 'shopping-cart',
        'color': '#7F54B3',
        'auth_type': 'api_key',
        'description': 'WooCommerce REST API (WordPress).',
        'fields': [
            {'key': 'site_url',       'label': 'URL da loja',     'type': 'text', 'required': True},
            {'key': 'consumer_key',    'label': 'Consumer Key',    'type': 'text', 'required': True},
            {'key': 'consumer_secret', 'label': 'Consumer Secret', 'type': 'password', 'required': True},
        ],
        'actions': ['create_order'],
        'triggers': ['new_order'],
    },

    # ─ Webhooks customizados ─────────────────────────────────
    'webhook': {
        'name': 'Webhook customizado',
        'category': 'developer',
        'icon': 'webhook',
        'color': '#A855F7',
        'auth_type': 'webhook',
        'description': 'Receba/dispare requisições HTTP para qualquer API.',
        'fields': [
            {'key': 'url',     'label': 'Endpoint URL',          'type': 'text', 'required': True},
            {'key': 'method',  'label': 'Método HTTP',           'type': 'select', 'options': ['POST', 'PUT', 'PATCH', 'GET'], 'default': 'POST'},
            {'key': 'headers', 'label': 'Headers JSON (opcional)', 'type': 'textarea', 'placeholder': '{"Authorization": "Bearer ..."}'},
        ],
        'actions': ['call_endpoint'],
        'triggers': ['incoming_webhook'],
    },
}

CATEGORIES = {
    'communication': {'name': 'Comunicação', 'icon': 'mail'},
    'messaging':     {'name': 'Mensageria',  'icon': 'message-circle'},
    'payments':      {'name': 'Pagamentos',  'icon': 'credit-card'},
    'banking':       {'name': 'Open Finance / Bancos', 'icon': 'landmark'},
    'productivity':  {'name': 'Produtividade', 'icon': 'briefcase'},
    'ecommerce':     {'name': 'E-commerce', 'icon': 'shopping-bag'},
    'developer':     {'name': 'Desenvolvedor', 'icon': 'code'},
}


# ── API pública do service ───────────────────────────────────────────────────
def list_providers() -> list:
    """Catálogo completo (para o marketplace)."""
    return [{'id': pid, **{k: v for k, v in p.items() if k != 'fields'}}
            for pid, p in PROVIDERS.items()]


def get_provider(provider_id: str) -> dict | None:
    p = PROVIDERS.get(provider_id)
    if not p:
        return None
    return {'id': provider_id, **p}


def list_user_integrations(user_id: int) -> list:
    """Integrações conectadas do usuário."""
    items = Integration.query.filter_by(user_id=user_id).order_by(
        Integration.created_at.desc()
    ).all()
    out = []
    for i in items:
        d = i.to_dict()
        meta = PROVIDERS.get(i.provider, {})
        d['provider_name'] = meta.get('name', i.provider)
        d['icon']          = meta.get('icon', 'plug')
        d['color']         = meta.get('color', '#888')
        d['category']      = meta.get('category')
        out.append(d)
    return out


def connect_integration(user_id: int, provider: str, name: str,
                        credentials: dict, config: dict | None = None) -> tuple[bool, str, dict | None]:
    """Cria ou atualiza uma integração do usuário com credenciais cifradas."""
    meta = PROVIDERS.get(provider)
    if not meta:
        return False, f'Provider desconhecido: {provider}', None

    # Validação básica dos campos required
    for f in meta.get('fields', []):
        if f.get('required') and not credentials.get(f['key']):
            return False, f"Campo obrigatório ausente: {f['label']}", None

    enc = encrypt_api_key(json.dumps(credentials))

    integ = Integration.query.filter_by(user_id=user_id, provider=provider).first()
    if integ:
        integ.credentials_encrypted = enc
        integ.config = json.dumps(config or {})
        integ.name = name or meta['name']
        integ.auth_type = meta['auth_type']
        integ.status = 'connected'
        integ.last_error = None
    else:
        integ = Integration(
            user_id=user_id,
            provider=provider,
            name=name or meta['name'],
            auth_type=meta['auth_type'],
            credentials_encrypted=enc,
            config=json.dumps(config or {}),
            status='connected',
        )
        db.session.add(integ)

    db.session.commit()
    return True, 'Integração conectada!', integ.to_dict()


def disconnect_integration(user_id: int, integration_id: int) -> tuple[bool, str]:
    integ = Integration.query.filter_by(id=integration_id, user_id=user_id).first()
    if not integ:
        return False, 'Integração não encontrada.'
    db.session.delete(integ)
    db.session.commit()
    return True, 'Integração desconectada.'


def test_integration(user_id: int, integration_id: int) -> tuple[bool, str]:
    """Stub de teste — em produção dispararia ping no provedor."""
    integ = Integration.query.filter_by(id=integration_id, user_id=user_id).first()
    if not integ:
        return False, 'Integração não encontrada.'
    integ.last_sync_at = datetime.utcnow()
    integ.status = 'connected'
    integ.last_error = None
    db.session.commit()
    return True, f'Conexão com {integ.provider} validada.'


def get_credentials(user_id: int, provider: str) -> dict | None:
    """Recupera credenciais (descriptografadas) — usar somente no backend."""
    integ = Integration.query.filter_by(user_id=user_id, provider=provider).first()
    if not integ or not integ.credentials_encrypted:
        return None
    try:
        return json.loads(decrypt_api_key(integ.credentials_encrypted))
    except Exception:
        return None
