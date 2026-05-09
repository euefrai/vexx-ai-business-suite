from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user
from services.billing_service import get_plans, get_current_plan, upgrade_plan, get_usage_stats

billing_bp = Blueprint('billing', __name__)


@billing_bp.route('/billing')
@login_required
def billing_page():
    return render_template('billing.html')


@billing_bp.route('/pricing')
def pricing_page():
    return render_template('pricing.html')


@billing_bp.route('/api/billing/plans')
def api_plans():
    return jsonify({'success': True, 'data': get_plans()})


@billing_bp.route('/api/billing/current')
@login_required
def api_current_plan():
    data = get_current_plan(current_user)
    return jsonify({'success': True, 'data': data})


@billing_bp.route('/api/billing/usage')
@login_required
def api_usage():
    data = get_usage_stats(current_user)
    return jsonify({'success': True, 'data': data})


@billing_bp.route('/api/billing/upgrade', methods=['POST'])
@login_required
def api_upgrade():
    data = request.get_json() or {}
    new_plan = data.get('plan', '')
    ok, msg = upgrade_plan(current_user, new_plan)
    return jsonify({'success': ok, 'message': msg}), (200 if ok else 400)
