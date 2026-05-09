from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user
from services.finance_service import (
    list_transactions, create_transaction, delete_transaction,
    get_financial_summary, list_invoices, create_invoice, update_invoice_status,
)
from services.dashboard_service import get_monthly_revenue_chart
from utils.permissions import check_limit

finance_bp = Blueprint('finance', __name__)


@finance_bp.route('/finance')
@login_required
def finance_page():
    return render_template('finance.html')


@finance_bp.route('/api/finance/summary')
@login_required
def api_summary():
    data = get_financial_summary(current_user.id)
    return jsonify({'success': True, 'data': data})


@finance_bp.route('/api/finance/chart')
@login_required
def api_finance_chart():
    chart = get_monthly_revenue_chart(current_user.id)
    return jsonify({'success': True, 'data': chart})


@finance_bp.route('/api/finance/transactions')
@login_required
def api_list_transactions():
    tx_type = request.args.get('type', '')
    limit = int(request.args.get('limit', 50))
    data = list_transactions(current_user.id, tx_type, limit)
    return jsonify({'success': True, 'data': data})


@finance_bp.route('/api/finance/transactions', methods=['POST'])
@login_required
def api_create_transaction():
    data = request.get_json() or {}
    ok, msg, tx = create_transaction(current_user.id, data)
    status = 201 if ok else 400
    return jsonify({'success': ok, 'message': msg, 'data': tx}), status


@finance_bp.route('/api/finance/transactions/<int:tx_id>', methods=['DELETE'])
@login_required
def api_delete_transaction(tx_id):
    ok, msg = delete_transaction(current_user.id, tx_id)
    return jsonify({'success': ok, 'message': msg}), (200 if ok else 404)


@finance_bp.route('/api/finance/invoices')
@login_required
def api_list_invoices():
    status = request.args.get('status', '')
    data = list_invoices(current_user.id, status)
    return jsonify({'success': True, 'data': data})


@finance_bp.route('/api/finance/invoices', methods=['POST'])
@login_required
def api_create_invoice():
    allowed, msg = check_limit(current_user, 'invoices')
    if not allowed:
        return jsonify({'success': False, 'error': msg}), 403

    data = request.get_json() or {}
    ok, msg, invoice = create_invoice(current_user.id, data)
    status = 201 if ok else 400
    return jsonify({'success': ok, 'message': msg, 'data': invoice}), status


@finance_bp.route('/api/finance/invoices/<int:invoice_id>/status', methods=['PATCH'])
@login_required
def api_update_invoice_status(invoice_id):
    data = request.get_json() or {}
    ok, msg = update_invoice_status(current_user.id, invoice_id, data.get('status', ''))
    return jsonify({'success': ok, 'message': msg}), (200 if ok else 400)
