from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user
from database.db import db
from database.models import APIKey
from utils.security import encrypt_api_key, decrypt_api_key
from utils.validators import sanitize_string

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/settings')
@login_required
def settings_page():
    return render_template('settings.html')


@settings_bp.route('/api/settings/profile', methods=['GET'])
@login_required
def api_get_profile():
    return jsonify({'success': True, 'data': current_user.to_dict()})


@settings_bp.route('/api/settings/profile', methods=['PUT'])
@login_required
def api_update_profile():
    from services.auth_service import update_profile
    data = request.get_json() or {}
    ok, msg = update_profile(current_user, data)
    return jsonify({'success': ok, 'message': msg})


@settings_bp.route('/api/settings/password', methods=['PUT'])
@login_required
def api_change_password():
    from services.auth_service import change_password
    data = request.get_json() or {}
    ok, msg = change_password(
        current_user,
        data.get('current_password', ''),
        data.get('new_password', ''),
    )
    return jsonify({'success': ok, 'message': msg}), (200 if ok else 400)


@settings_bp.route('/api/settings/api-keys')
@login_required
def api_list_keys():
    keys = APIKey.query.filter_by(user_id=current_user.id).all()
    return jsonify({'success': True, 'data': [k.to_dict() for k in keys]})


@settings_bp.route('/api/settings/api-keys', methods=['POST'])
@login_required
def api_add_key():
    data = request.get_json() or {}
    provider = sanitize_string(data.get('provider', ''), 50)
    raw_key = sanitize_string(data.get('key', ''), 500)
    name = sanitize_string(data.get('name', provider), 100)

    if not provider or not raw_key:
        return jsonify({'success': False, 'error': 'Provider e key são obrigatórios.'}), 400

    existing = APIKey.query.filter_by(user_id=current_user.id, provider=provider, is_active=True).first()
    if existing:
        existing.key_encrypted = encrypt_api_key(raw_key)
        existing.name = name
    else:
        key_obj = APIKey(
            user_id=current_user.id,
            name=name,
            key_encrypted=encrypt_api_key(raw_key),
            provider=provider,
        )
        db.session.add(key_obj)

    db.session.commit()
    return jsonify({'success': True, 'message': f'API Key para {provider} salva.'})


@settings_bp.route('/api/settings/api-keys/<int:key_id>', methods=['DELETE'])
@login_required
def api_delete_key(key_id):
    key_obj = APIKey.query.filter_by(id=key_id, user_id=current_user.id).first()
    if not key_obj:
        return jsonify({'success': False, 'error': 'Key não encontrada.'}), 404
    db.session.delete(key_obj)
    db.session.commit()
    return jsonify({'success': True, 'message': 'API Key removida.'})
