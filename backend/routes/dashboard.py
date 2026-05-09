from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required, current_user
from services.dashboard_service import get_dashboard_stats, get_recent_activity, get_monthly_revenue_chart
from database.db import db
from database.models import Notification

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@login_required
def dashboard_page():
    return render_template('dashboard.html')


@dashboard_bp.route('/api/dashboard/stats')
@login_required
def api_stats():
    stats = get_dashboard_stats(current_user.id)
    return jsonify({'success': True, 'data': stats})


@dashboard_bp.route('/api/dashboard/activity')
@login_required
def api_activity():
    activity = get_recent_activity(current_user.id)
    return jsonify({'success': True, 'data': activity})


@dashboard_bp.route('/api/dashboard/chart')
@login_required
def api_chart():
    chart = get_monthly_revenue_chart(current_user.id)
    return jsonify({'success': True, 'data': chart})


# ── Notifications ────────────────────────────────────────────────────────────

@dashboard_bp.route('/api/notifications')
@login_required
def api_notifications():
    items = Notification.query.filter_by(user_id=current_user.id) \
        .order_by(Notification.created_at.desc()).limit(30).all()
    unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'success': True, 'data': [n.to_dict() for n in items], 'unread': unread})


@dashboard_bp.route('/api/notifications/<int:notif_id>/read', methods=['PATCH'])
@login_required
def api_mark_read(notif_id):
    n = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first()
    if not n:
        return jsonify({'success': False, 'error': 'Não encontrada.'}), 404
    n.is_read = True
    db.session.commit()
    return jsonify({'success': True})


@dashboard_bp.route('/api/notifications/read-all', methods=['POST'])
@login_required
def api_mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False) \
        .update({Notification.is_read: True})
    db.session.commit()
    return jsonify({'success': True})
