from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user
from services.analytics_service import (
    get_analytics_overview, get_leads_by_stage,
    get_revenue_trend, get_top_categories,
)

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/analytics')
@login_required
def analytics_page():
    return render_template('analytics.html')


@analytics_bp.route('/api/analytics/overview')
@login_required
def api_overview():
    data = get_analytics_overview(current_user.id)
    return jsonify({'success': True, 'data': data})


@analytics_bp.route('/api/analytics/leads-by-stage')
@login_required
def api_leads_by_stage():
    data = get_leads_by_stage(current_user.id)
    return jsonify({'success': True, 'data': data})


@analytics_bp.route('/api/analytics/revenue-trend')
@login_required
def api_revenue_trend():
    days = int(request.args.get('days', 30))
    data = get_revenue_trend(current_user.id, min(days, 90))
    return jsonify({'success': True, 'data': data})


@analytics_bp.route('/api/analytics/top-categories')
@login_required
def api_top_categories():
    data = get_top_categories(current_user.id)
    return jsonify({'success': True, 'data': data})
