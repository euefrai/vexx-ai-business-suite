import os
import secrets
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _require_secret(env_var: str, fallback: str, prod_safe: bool = False) -> str:
    """Em prod, força que SECRET_KEY/JWT venham do env. Caso contrário, gera um aleatório seguro."""
    val = os.environ.get(env_var)
    if val:
        return val
    if os.environ.get('FLASK_ENV') == 'production' and not prod_safe:
        raise RuntimeError(
            f'{env_var} não definida em produção. Defina via variável de ambiente.'
        )
    return fallback


class Config:
    """Configuração base — herdada por dev e prod."""
    SECRET_KEY = _require_secret('SECRET_KEY', 'vexx-dev-only-' + secrets.token_hex(8))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = _require_secret('JWT_SECRET_KEY', 'vexx-jwt-dev-' + secrets.token_hex(8))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    # ── Sessions / Cookies ───────────────────────────────────────────────
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True             # JS não consegue ler o cookie de sessão
    SESSION_COOKIE_SAMESITE = 'Lax'            # mitiga CSRF em GETs cross-site
    SESSION_COOKIE_NAME = 'vexx_session'
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'

    # ── CSRF ─────────────────────────────────────────────────────────────
    WTF_CSRF_TIME_LIMIT = 3600 * 8             # token válido por 8h
    WTF_CSRF_SSL_STRICT = False                # permite dev em HTTP
    WTF_CSRF_HEADERS = ['X-CSRFToken', 'X-CSRF-Token']

    # ── Limites de upload (futuro) ───────────────────────────────────────
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024      # 10 MB

    # ── Sentry (opcional) ────────────────────────────────────────────────
    SENTRY_DSN = os.environ.get('SENTRY_DSN', '')

    # ── Stripe (opcional em dev — sem isso o billing fica em modo demo) ──
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
    STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
    STRIPE_PRICE_PRO = os.environ.get('STRIPE_PRICE_PRO', '')          # price_xxx (Pro mensal)
    STRIPE_PRICE_ENTERPRISE = os.environ.get('STRIPE_PRICE_ENTERPRISE', '')  # price_xxx (Enterprise mensal)
    STRIPE_TRIAL_DAYS = int(os.environ.get('STRIPE_TRIAL_DAYS', '14'))
    PUBLIC_BASE_URL = os.environ.get('PUBLIC_BASE_URL', 'http://localhost:5000')


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'database', 'vexx.db')}"
    # Cookies funcionam sobre HTTP em dev
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = True


class ProductionConfig(Config):
    DEBUG = False
    _db_url = os.environ.get('DATABASE_URL', '')
    if _db_url and _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
        
    SQLALCHEMY_DATABASE_URI = _db_url or f"sqlite:///{os.path.join(BASE_DIR, 'database', 'vexx.db')}"
    # Cookies só trafegam por HTTPS
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    REMEMBER_COOKIE_SECURE = True
    WTF_CSRF_ENABLED = True
    PREFERRED_URL_SCHEME = 'https'


class TestingConfig(Config):
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False                   # facilita testes
    SESSION_COOKIE_SECURE = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}
