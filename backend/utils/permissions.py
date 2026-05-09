from functools import wraps
from flask import jsonify
from flask_login import current_user


PLAN_LIMITS = {
    'free': {
        'contacts': 100,
        'leads': 50,
        'automations': 3,
        'ai_requests': 20,
        'invoices': 10,
    },
    'pro': {
        'contacts': 5000,
        'leads': 2000,
        'automations': 50,
        'ai_requests': 500,
        'invoices': 500,
    },
    'enterprise': {
        'contacts': -1,   # unlimited
        'leads': -1,
        'automations': -1,
        'ai_requests': -1,
        'invoices': -1,
    },
}


def requires_plan(*plans):
    """Decorator to restrict route to certain plans."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'error': 'Authentication required'}), 401
            if current_user.plan not in plans:
                return jsonify({
                    'error': 'Upgrade required',
                    'message': f'This feature requires a {" or ".join(plans)} plan.',
                    'current_plan': current_user.plan,
                }), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def check_limit(user, resource: str) -> tuple[bool, str]:
    """Returns (allowed, message). -1 limit means unlimited."""
    limit = PLAN_LIMITS.get(user.plan, {}).get(resource, 0)
    if limit == -1:
        return True, ''

    from database.models import Contact, Lead, Automation, Invoice
    counts = {
        'contacts': lambda: Contact.query.filter_by(user_id=user.id).count(),
        'leads': lambda: Lead.query.filter_by(user_id=user.id).count(),
        'automations': lambda: Automation.query.filter_by(user_id=user.id).count(),
        'invoices': lambda: Invoice.query.filter_by(user_id=user.id).count(),
        'ai_requests': lambda: user.ai_usage_count,
    }

    current = counts.get(resource, lambda: 0)()
    if current >= limit:
        return False, f"Limite do plano {user.plan} atingido ({limit} {resource}). Faça upgrade para continuar."
    return True, ''
