from database.db import db
from database.models import User

PLANS = {
    'free': {
        'name': 'Free',
        'price': 0,
        'currency': 'BRL',
        'features': [
            '100 contatos',
            '50 leads',
            '3 automações',
            '20 requisições IA/mês',
            '10 faturas',
            'Suporte por e-mail',
        ],
        'limits': {
            'contacts': 100, 'leads': 50, 'automations': 3, 'ai_requests': 20, 'invoices': 10
        },
    },
    'pro': {
        'name': 'Pro',
        'price': 197,
        'currency': 'BRL',
        'features': [
            '5.000 contatos',
            '2.000 leads',
            '50 automações',
            '500 requisições IA/mês',
            '500 faturas',
            'Analytics avançado',
            'Suporte prioritário',
        ],
        'limits': {
            'contacts': 5000, 'leads': 2000, 'automations': 50, 'ai_requests': 500, 'invoices': 500
        },
    },
    'enterprise': {
        'name': 'Enterprise',
        'price': 497,
        'currency': 'BRL',
        'features': [
            'Contatos ilimitados',
            'Leads ilimitados',
            'Automações ilimitadas',
            'IA ilimitada',
            'Faturas ilimitadas',
            'API dedicada',
            'Suporte 24/7',
            'Onboarding personalizado',
        ],
        'limits': {
            'contacts': -1, 'leads': -1, 'automations': -1, 'ai_requests': -1, 'invoices': -1
        },
    },
}


def get_plans() -> list:
    return [{'id': k, **v} for k, v in PLANS.items()]


def get_current_plan(user: User) -> dict:
    plan_data = PLANS.get(user.plan, PLANS['free'])
    return {
        'plan': user.plan,
        **plan_data,
        'user_since': user.created_at.isoformat(),
    }


def upgrade_plan(user: User, new_plan: str) -> tuple[bool, str]:
    if new_plan not in PLANS:
        return False, 'Plano inválido.'
    if user.plan == new_plan:
        return False, f'Você já está no plano {new_plan}.'

    # In production this would integrate with Stripe/Mercado Pago
    user.plan = new_plan
    db.session.commit()
    return True, f'Plano atualizado para {PLANS[new_plan]["name"]}.'


def get_usage_stats(user: User) -> dict:
    from database.models import Contact, Lead, Automation, Invoice
    return {
        'contacts': {
            'used': Contact.query.filter_by(user_id=user.id).count(),
            'limit': PLANS[user.plan]['limits']['contacts'],
        },
        'leads': {
            'used': Lead.query.filter_by(user_id=user.id).count(),
            'limit': PLANS[user.plan]['limits']['leads'],
        },
        'automations': {
            'used': Automation.query.filter_by(user_id=user.id).count(),
            'limit': PLANS[user.plan]['limits']['automations'],
        },
        'ai_requests': {
            'used': user.ai_usage_count,
            'limit': PLANS[user.plan]['limits']['ai_requests'],
        },
        'invoices': {
            'used': Invoice.query.filter_by(user_id=user.id).count(),
            'limit': PLANS[user.plan]['limits']['invoices'],
        },
    }
