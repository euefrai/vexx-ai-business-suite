from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user
from services.crm_service import (
    list_contacts, create_contact, update_contact, delete_contact,
    list_leads, create_lead, update_lead, update_lead_stage, delete_lead,
    get_pipeline_summary,
)
from utils.permissions import check_limit

crm_bp = Blueprint('crm', __name__)


@crm_bp.route('/crm')
@login_required
def crm_page():
    return render_template('crm.html')


# ── Contacts ─────────────────────────────────────────────────────────────────

@crm_bp.route('/api/crm/contacts')
@login_required
def api_list_contacts():
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    data = list_contacts(current_user.id, search, status)
    return jsonify({'success': True, 'data': data, 'count': len(data)})


@crm_bp.route('/api/crm/contacts', methods=['POST'])
@login_required
def api_create_contact():
    allowed, msg = check_limit(current_user, 'contacts')
    if not allowed:
        return jsonify({'success': False, 'error': msg}), 403

    data = request.get_json() or {}
    ok, msg, contact = create_contact(current_user.id, data)
    status = 201 if ok else 400
    return jsonify({'success': ok, 'message': msg, 'data': contact}), status


@crm_bp.route('/api/crm/contacts/<int:contact_id>', methods=['PUT'])
@login_required
def api_update_contact(contact_id):
    data = request.get_json() or {}
    ok, msg = update_contact(current_user.id, contact_id, data)
    return jsonify({'success': ok, 'message': msg}), (200 if ok else 400)


@crm_bp.route('/api/crm/contacts/<int:contact_id>', methods=['DELETE'])
@login_required
def api_delete_contact(contact_id):
    ok, msg = delete_contact(current_user.id, contact_id)
    return jsonify({'success': ok, 'message': msg}), (200 if ok else 404)


# ── Leads ─────────────────────────────────────────────────────────────────────

@crm_bp.route('/api/crm/leads')
@login_required
def api_list_leads():
    stage = request.args.get('stage', '')
    data = list_leads(current_user.id, stage)
    return jsonify({'success': True, 'data': data})


@crm_bp.route('/api/crm/leads', methods=['POST'])
@login_required
def api_create_lead():
    allowed, msg = check_limit(current_user, 'leads')
    if not allowed:
        return jsonify({'success': False, 'error': msg}), 403

    data = request.get_json() or {}
    ok, msg, lead = create_lead(current_user.id, data)
    status = 201 if ok else 400
    return jsonify({'success': ok, 'message': msg, 'data': lead}), status


@crm_bp.route('/api/crm/leads/<int:lead_id>', methods=['PUT'])
@login_required
def api_update_lead(lead_id):
    data = request.get_json() or {}
    ok, msg = update_lead(current_user.id, lead_id, data)
    return jsonify({'success': ok, 'message': msg}), (200 if ok else 400)


@crm_bp.route('/api/crm/leads/<int:lead_id>/stage', methods=['PATCH'])
@login_required
def api_update_lead_stage(lead_id):
    data = request.get_json() or {}
    stage = data.get('stage', '')
    ok, msg = update_lead_stage(current_user.id, lead_id, stage)
    return jsonify({'success': ok, 'message': msg}), (200 if ok else 400)


@crm_bp.route('/api/crm/leads/<int:lead_id>', methods=['DELETE'])
@login_required
def api_delete_lead(lead_id):
    ok, msg = delete_lead(current_user.id, lead_id)
    return jsonify({'success': ok, 'message': msg}), (200 if ok else 404)


@crm_bp.route('/api/crm/pipeline')
@login_required
def api_pipeline():
    data = get_pipeline_summary(current_user.id)
    return jsonify({'success': True, 'data': data})
