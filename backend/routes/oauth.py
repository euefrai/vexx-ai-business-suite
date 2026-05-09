"""
VEXX AI — OAuth flow routes (Google).
"""

from flask import Blueprint, redirect, request, jsonify, url_for
from flask_login import login_required, current_user
from services.oauth_service import (
    build_authorize_url, exchange_code, fetch_userinfo,
    save_oauth_integration, is_configured, get_expected_redirect_uri,
)
from database.db import csrf

oauth_bp = Blueprint('oauth', __name__)


def _safe_base_url():
    """Google OAuth rejeita IPs privados (192.168.x.x, 10.x.x.x, etc).
    Força localhost quando o host é um IP privado."""
    import re
    host_url = request.host_url  # ex: http://192.168.1.11:5000/
    # Detecta IP privado no host
    if re.search(r'//(?:192\.168\.|10\.|172\.(?:1[6-9]|2[0-9]|3[01])\.)', host_url):
        # Extrai porta e reescreve com localhost
        from urllib.parse import urlparse
        parsed = urlparse(host_url)
        port = parsed.port or 5000
        return f'http://localhost:{port}/'
    return host_url


@oauth_bp.route('/oauth/google/status')
@login_required
def google_status():
    configured = is_configured()
    return jsonify({
        'success': True,
        'configured': configured,
        'redirect_uri': get_expected_redirect_uri() if configured else None,
    })


@oauth_bp.route('/oauth/google/authorize')
def google_authorize():
    """Redireciona para Google. Provider: gmail | google_sheets | google_calendar.
    Aceita user_id via sessão (login_required) ou via query param (redirect de IP privado)."""
    from flask_login import current_user as cu
    provider = request.args.get('provider', 'gmail')

    # Determina user_id: sessão preferencial, senão query param (para redirects localhost)
    user_id = None
    if cu and cu.is_authenticated:
        user_id = cu.id
    else:
        uid_param = request.args.get('uid')
        if uid_param:
            try:
                user_id = int(uid_param)
            except (ValueError, TypeError):
                pass

    if not user_id:
        return jsonify({'success': False, 'error': 'Sessão expirada. Faça login novamente.'}), 401

    base_url = _safe_base_url()

    if not is_configured():
        return jsonify({
            'success': False,
            'error': 'OAuth Google não configurado. Defina GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET no .env do servidor.',
        }), 503

    url, state = build_authorize_url(user_id, provider, base_url)
    if not url:
        return jsonify({'success': False, 'error': 'Provider inválido.'}), 400

    return redirect(url)


@oauth_bp.route('/oauth/google/callback')
@csrf.exempt
def google_callback():
    """Callback do Google após o usuário autorizar."""
    code  = request.args.get('code')
    state = request.args.get('state', '')
    error = request.args.get('error')

    if error:
        return f'<h2>Erro de OAuth: {error}</h2><a href="/automation">Voltar</a>', 400

    if not code or not state:
        return '<h2>Parâmetros ausentes</h2>', 400

    try:
        user_id_str, provider, _ = state.split(':', 2)
        user_id = int(user_id_str)
    except (ValueError, IndexError):
        return '<h2>State inválido</h2>', 400

    try:
        base_url = _safe_base_url()
        tokens   = exchange_code(code, base_url)
        userinfo = fetch_userinfo(tokens['access_token'])
        save_oauth_integration(user_id, provider, tokens, userinfo)
    except Exception as e:
        return f'<h2>Erro ao trocar tokens: {e}</h2><a href="/automation">Voltar</a>', 500

    # Página de sucesso simples
    return f'''
    <!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
    <title>Conectado — VEXX AI</title>
    <style>
      body {{ font-family: system-ui, sans-serif; background:#0c0c18; color:#eef0f8;
              display:grid; place-items:center; min-height:100vh; margin:0; }}
      .card {{ background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1);
               border-radius:16px; padding:40px; text-align:center; max-width:420px; }}
      .icon {{ font-size:48px; margin-bottom:12px; }}
      a.btn {{ display:inline-block; padding:10px 20px; background:#6d28d9;
               color:#fff; text-decoration:none; border-radius:10px; margin-top:18px; }}
    </style></head>
    <body>
      <div class="card">
        <div class="icon">✅</div>
        <h2>{provider.replace('_', ' ').title()} conectado!</h2>
        <p style="color:#818da6">Email autorizado: <strong style="color:#a78bfa">{userinfo.get("email")}</strong></p>
        <p style="color:#818da6">Você já pode usar este provider em automações.</p>
        <a href="/automation" class="btn">← Voltar para Automação</a>
      </div>
      <script>setTimeout(() => window.location = '/automation', 3000);</script>
    </body></html>
    '''
