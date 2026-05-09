from datetime import datetime, date
from flask_login import UserMixin
from database.db import db


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    company = db.Column(db.String(100))
    plan = db.Column(db.String(20), default='free')  # free, pro, enterprise
    is_active = db.Column(db.Boolean, default=True)
    is_email_verified = db.Column(db.Boolean, default=False)
    last_login_at = db.Column(db.DateTime)
    ai_usage_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ── Stripe / assinatura ──────────────────────────────────────
    stripe_customer_id = db.Column(db.String(80), index=True)
    stripe_subscription_id = db.Column(db.String(80), index=True)
    # active | trialing | past_due | canceled | incomplete | unpaid | none
    subscription_status = db.Column(db.String(30), default='none')
    trial_ends_at = db.Column(db.DateTime)
    current_period_ends_at = db.Column(db.DateTime)
    cancel_at_period_end = db.Column(db.Boolean, default=False)

    contacts = db.relationship('Contact', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    leads = db.relationship('Lead', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    automations = db.relationship('Automation', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    conversations = db.relationship('AIConversation', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    api_keys = db.relationship('APIKey', backref='owner', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def to_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'email': self.email,
            'company': self.company,
            'plan': self.plan,
            'is_email_verified': bool(self.is_email_verified),
            'is_active': bool(self.is_active),
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'ai_usage_count': self.ai_usage_count,
            'created_at': self.created_at.isoformat(),
            'subscription_status': self.subscription_status or 'none',
            'trial_ends_at': self.trial_ends_at.isoformat() if self.trial_ends_at else None,
            'current_period_ends_at': self.current_period_ends_at.isoformat() if self.current_period_ends_at else None,
            'cancel_at_period_end': bool(self.cancel_at_period_end),
        }

    @property
    def trial_days_left(self) -> int:
        if not self.trial_ends_at:
            return 0
        delta = self.trial_ends_at - datetime.utcnow()
        return max(0, delta.days)

    @property
    def has_active_subscription(self) -> bool:
        return self.subscription_status in ('active', 'trialing')


class Contact(db.Model):
    __tablename__ = 'contacts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(30))
    company = db.Column(db.String(100))
    position = db.Column(db.String(100))
    status = db.Column(db.String(20), default='active')  # active, inactive, prospect
    notes = db.Column(db.Text)
    tags = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    leads = db.relationship('Lead', backref='contact', lazy='dynamic')
    invoices = db.relationship('Invoice', backref='contact', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'company': self.company,
            'position': self.position,
            'status': self.status,
            'notes': self.notes,
            'tags': self.tags,
            'created_at': self.created_at.isoformat(),
        }


class Lead(db.Model):
    __tablename__ = 'leads'

    STAGES = ['prospect', 'qualified', 'proposal', 'negotiation', 'closed_won', 'closed_lost']

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    stage = db.Column(db.String(30), default='prospect')
    value = db.Column(db.Float, default=0.0)
    probability = db.Column(db.Integer, default=10)
    expected_close = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'stage': self.stage,
            'value': self.value,
            'probability': self.probability,
            'expected_close': self.expected_close.isoformat() if self.expected_close else None,
            'notes': self.notes,
            'contact_id': self.contact_id,
            'contact_name': self.contact.name if self.contact else None,
            'created_at': self.created_at.isoformat(),
        }


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # income, expense
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    category = db.Column(db.String(50))
    date = db.Column(db.Date, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'amount': self.amount,
            'description': self.description,
            'category': self.category,
            'date': self.date.isoformat() if self.date else None,
            'created_at': self.created_at.isoformat(),
        }


class Invoice(db.Model):
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=True)
    invoice_number = db.Column(db.String(20), unique=True)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, paid, overdue
    due_date = db.Column(db.Date)
    description = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'amount': self.amount,
            'status': self.status,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'description': self.description,
            'contact_name': self.contact.name if self.contact else None,
            'created_at': self.created_at.isoformat(),
        }


class Automation(db.Model):
    __tablename__ = 'automations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300))
    trigger = db.Column(db.String(50))   # new_lead, payment, schedule, etc.
    action = db.Column(db.String(50))    # send_email, create_task, notify, etc.
    enabled = db.Column(db.Boolean, default=True)
    runs_count = db.Column(db.Integer, default=0)
    last_run = db.Column(db.DateTime)
    config = db.Column(db.Text)           # JSON config stored as text
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'trigger': self.trigger,
            'action': self.action,
            'enabled': self.enabled,
            'runs_count': self.runs_count,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'created_at': self.created_at.isoformat(),
        }


class AIConversation(db.Model):
    __tablename__ = 'ai_conversations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), default='Nova Conversa')
    messages = db.Column(db.Text, default='[]')  # JSON array stored as text
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'title': self.title,
            'messages': json.loads(self.messages or '[]'),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class APIKey(db.Model):
    __tablename__ = 'api_keys'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100))
    key_encrypted = db.Column(db.String(500))  # stored encrypted
    provider = db.Column(db.String(50))          # openai, anthropic, deepseek, kimi
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'provider': self.provider,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
        }


class Company(db.Model):
    """Empresa / workspace. Base para multi-tenant: usuários podem
    pertencer a uma company e os recursos podem ser escopados nela."""
    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    cnpj = db.Column(db.String(20))
    industry = db.Column(db.String(80))
    size = db.Column(db.String(20))                     # 1-10, 11-50, 51-200, 200+
    timezone = db.Column(db.String(40), default='America/Sao_Paulo')
    currency = db.Column(db.String(8), default='BRL')
    monthly_goal = db.Column(db.Float, default=0.0)     # meta de receita mensal
    logo_url = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    members = db.relationship('CompanyMember', backref='company',
                              lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'cnpj': self.cnpj,
            'industry': self.industry, 'size': self.size,
            'timezone': self.timezone, 'currency': self.currency,
            'monthly_goal': self.monthly_goal,
            'logo_url': self.logo_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'member_count': self.members.count(),
        }


class CompanyMember(db.Model):
    """Vínculo User ↔ Company com role."""
    __tablename__ = 'company_members'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(20), default='member')   # owner | admin | member | viewer
    invited_email = db.Column(db.String(120))
    accepted = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('company_id', 'user_id', name='uq_company_user'),)

    def to_dict(self):
        return {
            'id': self.id, 'company_id': self.company_id, 'user_id': self.user_id,
            'role': self.role, 'invited_email': self.invited_email,
            'accepted': self.accepted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Integration(db.Model):
    __tablename__ = 'integrations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    provider = db.Column(db.String(50), nullable=False)   # gmail, whatsapp, stripe, ...
    name = db.Column(db.String(120))                      # rótulo amigável
    auth_type = db.Column(db.String(30))                  # oauth, api_key, smtp, webhook
    credentials_encrypted = db.Column(db.Text)            # JSON criptografado com Fernet
    config = db.Column(db.Text)                           # JSON livre por integração
    status = db.Column(db.String(20), default='connected')  # connected | error | revoked
    last_sync_at = db.Column(db.DateTime)
    last_error = db.Column(db.String(400))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'provider': self.provider,
            'name': self.name or self.provider,
            'auth_type': self.auth_type,
            'status': self.status,
            'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
            'last_error': self.last_error,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class AutomationLog(db.Model):
    __tablename__ = 'automation_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    automation_id = db.Column(db.Integer, db.ForeignKey('automations.id', ondelete='SET NULL'))
    status = db.Column(db.String(20))      # success | error | pending | skipped
    trigger = db.Column(db.String(60))
    action = db.Column(db.String(60))
    message = db.Column(db.String(400))
    payload = db.Column(db.Text)           # JSON
    duration_ms = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'automation_id': self.automation_id,
            'status': self.status,
            'trigger': self.trigger,
            'action': self.action,
            'message': self.message,
            'duration_ms': self.duration_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class AuthToken(db.Model):
    """Tokens descartáveis para email verification e password reset.
       Cada token é usado uma única vez (consumed_at != null)."""
    __tablename__ = 'auth_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token_hash = db.Column(db.String(128), nullable=False, unique=True, index=True)
    purpose = db.Column(db.String(30), nullable=False)  # email_verify | password_reset
    expires_at = db.Column(db.DateTime, nullable=False)
    consumed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_valid(self) -> bool:
        if self.consumed_at:
            return False
        return self.expires_at > datetime.utcnow()


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(40), default='info')  # info, success, warning, error, ai, lead
    title = db.Column(db.String(160))
    description = db.Column(db.String(400))
    is_read = db.Column(db.Boolean, default=False)
    link = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'title': self.title,
            'description': self.description,
            'is_read': self.is_read,
            'link': self.link,
            'created_at': self.created_at.isoformat(),
        }


def create_notification(user_id, type_, title, description='', link=''):
    """Helper to create a notification from anywhere in the codebase."""
    n = Notification(user_id=user_id, type=type_, title=title,
                     description=description, link=link)
    db.session.add(n)
    db.session.commit()
    return n
