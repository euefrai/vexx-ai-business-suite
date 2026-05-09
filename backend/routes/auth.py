from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
from flask_login import login_user, logout_user, login_required, current_user
from services.auth_service import register_user, authenticate_user, update_profile, change_password
from database.db import limiter

auth_bp = Blueprint('auth', __name__)


# ── Page routes ──────────────────────────────────────────────────────────────

def _no_cache(resp):
    """Força browser a sempre buscar versão fresca de páginas de auth."""
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


@auth_bp.route('/login', methods=['GET', 'POST'])
def login_page():
    from flask import make_response
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard_page'))

    # POST do formulário (fallback sem-JS)
    if request.method == 'POST':
        data = request.form.to_dict()
        email = data.get('email', '')
        password = data.get('password', '')
        ok, msg, user = authenticate_user(email, password)
        if not ok:
            return _no_cache(make_response(render_template('login.html', error=msg))), 401

        login_user(user, remember=data.get('remember', False))
        return redirect(url_for('dashboard.dashboard_page'))

    return _no_cache(make_response(render_template('login.html')))


@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit('5 per hour', methods=['POST'],
               error_message='Muitas tentativas de cadastro. Aguarde 1 hora.')
def register_page():
    from flask import make_response
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard_page'))

    # POST do formulário (fallback sem-JS)
    if request.method == 'POST':
        data = request.form.to_dict()
        ok, msg, user = register_user(data)
        if not ok:
            return _no_cache(make_response(render_template('register.html', error=msg))), 400
        login_user(user, remember=True)
        return redirect(url_for('dashboard.dashboard_page'))

    return _no_cache(make_response(render_template('register.html')))


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login_page'))


# ── API routes ────────────────────────────────────────────────────────────────

@auth_bp.route('/api/auth/register', methods=['POST'])
@limiter.limit('5 per hour', error_message='Muitas tentativas de cadastro. Tente novamente em 1 hora.')
def api_register():
    data = request.get_json() or request.form.to_dict()
    ok, msg, user = register_user(data)
    if not ok:
        return jsonify({'success': False, 'error': msg}), 400

    login_user(user, remember=True)
    return jsonify({'success': True, 'message': msg, 'user': user.to_dict()}), 201


@auth_bp.route('/api/auth/login', methods=['POST'])
@limiter.limit('10 per minute', error_message='Muitas tentativas de login. Aguarde 1 minuto.')
def api_login():
    """API JSON estrita — SEMPRE retorna JSON. Para fallback HTML use POST /login."""
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    email = data.get('email', '')
    password = data.get('password', '')

    ok, msg, user = authenticate_user(email, password)
    if not ok:
        return jsonify({'success': False, 'error': msg}), 401

    login_user(user, remember=bool(data.get('remember', False)))
    return jsonify({'success': True, 'message': msg, 'user': user.to_dict()})


@auth_bp.route('/api/auth/logout', methods=['POST'])
@login_required
def api_logout():
    logout_user()
    return jsonify({'success': True, 'message': 'Logout realizado.'})


@auth_bp.route('/api/auth/me')
@login_required
def api_me():
    return jsonify({'success': True, 'data': current_user.to_dict()})


@auth_bp.route('/api/auth/profile', methods=['PUT'])
@login_required
def api_update_profile():
    data = request.get_json() or {}
    ok, msg = update_profile(current_user, data)
    return jsonify({'success': ok, 'message': msg})


@auth_bp.route('/api/auth/password', methods=['PUT'])
@login_required
@limiter.limit('5 per minute')
def api_change_password():
    data = request.get_json() or {}
    ok, msg = change_password(
        current_user,
        data.get('current_password', ''),
        data.get('new_password', ''),
    )
    status = 200 if ok else 400
    return jsonify({'success': ok, 'message': msg}), status


# ═════════════════════════════════════════════════════════════════════════════
# Email verification
# ═════════════════════════════════════════════════════════════════════════════

@auth_bp.route('/api/auth/send-verification', methods=['POST'])
@login_required
@limiter.limit('3 per hour')
def api_send_verification():
    """(Re)envia email de verificação para o usuário logado."""
    if current_user.is_email_verified:
        return jsonify({'success': False, 'error': 'Email já verificado.'}), 400

    from services.token_service import create_token
    from services.email_service import send_verification_email
    raw = create_token(current_user.id, 'email_verify', hours_valid=24)
    ok, info = send_verification_email(current_user, raw)
    return jsonify({'success': ok, 'message': info}), (200 if ok else 500)


@auth_bp.route('/verify-email')
@limiter.limit('20 per hour')
def verify_email_page():
    """Endpoint do link enviado por email — ativa a conta."""
    from services.token_service import consume_token
    from database.db import db
    from datetime import datetime

    from flask import render_template_string
    raw = request.args.get('token', '')
    user = consume_token(raw, 'email_verify')

    if not user:
        return render_template_string(_VERIFY_RESULT_HTML, success=False,
                                      message='Link inválido ou expirado.'), 400

    user.is_email_verified = True
    db.session.commit()
    return render_template_string(_VERIFY_RESULT_HTML, success=True,
                                  message=f'Email {user.email} verificado!')


# ═════════════════════════════════════════════════════════════════════════════
# Password reset
# ═════════════════════════════════════════════════════════════════════════════

@auth_bp.route('/api/auth/forgot-password', methods=['POST'])
@limiter.limit('3 per hour')
def api_forgot_password():
    """Inicia o fluxo de reset. Sempre retorna sucesso (anti-enumeração)."""
    from services.token_service import create_token, revoke_user_tokens
    from services.email_service import send_password_reset_email
    from database.models import User

    data = request.get_json() or request.form.to_dict()
    email = (data.get('email', '') or '').strip().lower()

    if email:
        user = User.query.filter_by(email=email).first()
        if user:
            # Revoga tokens antigos antes de criar novo
            revoke_user_tokens(user.id, 'password_reset')
            raw = create_token(user.id, 'password_reset', hours_valid=1)
            send_password_reset_email(user, raw)

    # Sempre 200 — não revela se email existe
    return jsonify({
        'success': True,
        'message': 'Se a conta existir, você receberá um email com instruções em alguns minutos.',
    })


@auth_bp.route('/forgot-password')
def forgot_password_page():
    return render_template('forgot_password.html')


@auth_bp.route('/reset-password')
def reset_password_page():
    """Página acessada pelo link do email — formulário para nova senha."""
    raw = request.args.get('token', '')
    return render_template('reset_password.html', token=raw)


@auth_bp.route('/api/auth/reset-password', methods=['POST'])
@limiter.limit('5 per hour')
def api_reset_password():
    """Confirma a redefinição com token + nova senha."""
    from services.token_service import consume_token, revoke_user_tokens
    from utils.security import validate_password_strength
    from database.db import db, bcrypt

    data = request.get_json() or request.form.to_dict()
    raw = data.get('token', '')
    new_pw = data.get('new_password', '')

    ok, msg = validate_password_strength(new_pw)
    if not ok:
        return jsonify({'success': False, 'error': msg}), 400

    user = consume_token(raw, 'password_reset')
    if not user:
        return jsonify({'success': False, 'error': 'Link inválido ou expirado.'}), 400

    user.password_hash = bcrypt.generate_password_hash(new_pw).decode('utf-8')
    db.session.commit()
    revoke_user_tokens(user.id, 'password_reset')

    return jsonify({'success': True, 'message': 'Senha redefinida! Faça login com a nova senha.'})


_VERIFY_RESULT_HTML = '''
<!DOCTYPE html><html lang="pt-BR"><head>
<meta charset="UTF-8"><title>Verificação — VEXX AI</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  body { font-family: 'Inter', system-ui, sans-serif; background: linear-gradient(135deg, #07070f, #0c0c18); min-height: 100vh; display: grid; place-items: center; margin: 0; color: #eef0f8; }
  .card { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 18px; padding: 48px 40px; text-align: center; max-width: 440px; }
  .icon { font-size: 56px; margin-bottom: 8px; }
  h2 { margin: 8px 0 14px; font-size: 22px; }
  p  { color: #818da6; font-size: 14px; line-height: 1.6; }
  a.btn { display: inline-block; margin-top: 22px; padding: 12px 28px; background: linear-gradient(135deg, #6d28d9, #4338ca); color: #fff; text-decoration: none; border-radius: 12px; font-weight: 600; box-shadow: 0 4px 16px rgba(109,40,217,0.4); }
</style></head>
<body><div class="card">
  <div class="icon">{% if success %}✅{% else %}❌{% endif %}</div>
  <h2>{{ message }}</h2>
  <p>{% if success %}Você já pode acessar todos os recursos da plataforma.{% else %}O link pode ter expirado ou já foi usado.{% endif %}</p>
  <a href="/dashboard" class="btn">{% if success %}Ir para o Dashboard{% else %}Voltar para o login{% endif %}</a>
</div></body></html>'''
