import os
import sys
import logging

# Make sure imports resolve from the backend directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, redirect, url_for, jsonify
from config import config
from database.db import init_extensions, db
from sqlalchemy import inspect, text
from sqlalchemy.schema import CreateColumn


def _init_sentry(dsn: str):
    """Inicializa Sentry SDK se DSN estiver presente. Captura exceções e
       traços de performance automaticamente."""
    if not dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=dsn,
            integrations=[FlaskIntegration(), SqlalchemyIntegration()],
            traces_sample_rate=0.1,           # 10% de traces
            send_default_pii=False,           # nunca manda PII
            environment=os.environ.get('FLASK_ENV', 'development'),
        )
        logging.getLogger('vexx').info('Sentry inicializado.')
    except Exception as e:
        logging.warning(f'Falha ao iniciar Sentry: {e}')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, '..', 'frontend')


def create_app(env: str = 'development') -> Flask:
    app = Flask(
        __name__,
        template_folder=FRONTEND_DIR,
        static_folder=FRONTEND_DIR,
        static_url_path='',
    )
    app.config.from_object(config[env])

    # Logging estruturado mínimo
    if not app.debug:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s %(name)s [%(module)s:%(lineno)d] %(message)s',
        )

    # Sentry opt-in (defina SENTRY_DSN no .env para ativar)
    _init_sentry(app.config.get('SENTRY_DSN'))

    # Extensions
    init_extensions(app)

    # Health check (não levado por load balancers / monitoring)
    @app.route('/health')
    def health():
        return jsonify({'status': 'ok', 'service': 'vexx-ai'}), 200

    # CSRF refresh — frontend chama quando o token expira
    @app.route('/api/csrf')
    def api_csrf():
        from flask_wtf.csrf import generate_csrf
        return jsonify({'token': generate_csrf()})

    # Injeta automaticamente <meta name="csrf-token"> em todas as páginas HTML
    @app.after_request
    def inject_csrf_meta(response):
        try:
            ct = response.headers.get('Content-Type', '')
            if 'text/html' not in ct:
                return response
            from flask_wtf.csrf import generate_csrf
            token = generate_csrf()
            body = response.get_data(as_text=True)
            if '<meta name="csrf-token"' not in body and '</head>' in body:
                meta = f'<meta name="csrf-token" content="{token}">'
                body = body.replace('</head>', f'  {meta}\n</head>', 1)
                response.set_data(body)
                response.headers['Content-Length'] = str(len(response.get_data()))
        except Exception:
            pass
        return response

    # Blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.crm import crm_bp
    from routes.finance import finance_bp
    from routes.automation import automation_bp
    from routes.analytics import analytics_bp
    from routes.ai import ai_bp
    from routes.settings import settings_bp
    from routes.billing import billing_bp
    from routes.reports import reports_bp
    from routes.oauth import oauth_bp
    from routes.companies import companies_bp

    for bp in [auth_bp, dashboard_bp, crm_bp, finance_bp,
               automation_bp, analytics_bp, ai_bp, settings_bp, billing_bp,
               reports_bp, oauth_bp, companies_bp]:
        app.register_blueprint(bp)

    # Root redirect
    @app.route('/')
    def home():
        from flask import render_template
        return render_template('index.html')

    # Create DB tables and seed demo data on first run
    with app.app_context():
        import database.models  # noqa: F401 - registers all models in db.metadata
        db.create_all()
        _sync_dev_sqlite_schema(app)
        _seed_demo_data()

    # Boot background scheduler — somente no processo principal do Flask
    # (no debug mode o reloader sobe o app duas vezes)
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        from services.scheduler import init_scheduler
        try:
            init_scheduler(app)
        except Exception as e:
            print(f'⚠️  Scheduler não iniciado: {e}')

    return app


def _sync_dev_sqlite_schema(app: Flask):
    """Add newly introduced nullable/default columns to the local dev SQLite DB.

    db.create_all() creates missing tables, but it does not alter existing ones.
    This keeps the checked-in dev database usable when models gain optional fields.
    Production should use Flask-Migrate/Alembic migrations instead.
    """
    if not app.debug or db.engine.dialect.name != 'sqlite':
        return

    inspector = inspect(db.engine)
    for table in db.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue

        existing_columns = {column['name'] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing_columns:
                continue
            if not column.nullable and column.default is None and column.server_default is None:
                logging.warning(
                    'Coluna obrigatoria ausente nao sincronizada automaticamente: %s.%s',
                    table.name,
                    column.name,
                )
                continue

            ddl = f'ALTER TABLE {table.name} ADD COLUMN {CreateColumn(column).compile(db.engine)}'
            db.session.execute(text(ddl))
            logging.getLogger('vexx').info('Coluna adicionada ao SQLite dev: %s.%s', table.name, column.name)
    db.session.commit()


def _seed_demo_data():
    """Insert one demo user if the DB is empty."""
    from database.models import User
    from database.db import bcrypt

    if User.query.first():
        return

    demo = User(
        first_name='Admin',
        last_name='VEXX',
        email='admin@vexx.ai',
        password_hash=bcrypt.generate_password_hash('vexx2026').decode('utf-8'),
        company='VEXX AI Corp',
        plan='pro',
    )
    db.session.add(demo)
    db.session.commit()
    print('Demo user created: admin@vexx.ai / vexx2026')


if __name__ == '__main__':
    app = create_app('development')
    app.run(debug=True, host='0.0.0.0', port=5000)
