from flask import request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
bcrypt = Bcrypt()
csrf = CSRFProtect()


def _user_or_ip():
    """Identifica usuário logado para rate limit; cai no IP se anônimo."""
    try:
        if current_user and current_user.is_authenticated:
            return f'user:{current_user.id}'
    except Exception:
        pass
    return get_remote_address()


limiter = Limiter(
    key_func=_user_or_ip,
    default_limits=['1000 per hour'],
    storage_uri='memory://',  # produção: redis://...
)


def init_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db, directory='database/migrations')
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = 'auth.login_page'
    login_manager.login_message = 'Faça login para acessar esta página.'

    # ── CSRF erro retorna JSON em endpoints /api/* ─────────────────────
    @app.errorhandler(CSRFError)
    def handle_csrf(err):
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'CSRF token ausente ou inválido. Recarregue a página.',
            }), 400
        return f'<h2>CSRF inválido</h2><p>{err.description}</p>', 400

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': 'Não autenticado. Faça login.'}), 401
        from flask import redirect, url_for
        return redirect(url_for('auth.login_page', next=request.path))

    from database.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Disponibiliza csrf_token() em todos os templates Jinja
    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        return {'csrf_token': generate_csrf}
