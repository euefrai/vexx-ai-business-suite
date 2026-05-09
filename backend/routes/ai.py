from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user
from services.ai_service import (
    chat, list_conversations, delete_conversation,
    get_conversation, rename_conversation,
)
from utils.permissions import check_limit
from database.db import limiter

ai_bp = Blueprint('ai', __name__)


@ai_bp.route('/ai-assistant')
@login_required
def ai_page():
    return render_template('ai_assistant.html')


@ai_bp.route('/api/ai/chat', methods=['POST'])
@login_required
@limiter.limit('30 per minute', error_message='Muitas mensagens em sequência. Aguarde 1 minuto.')
def api_chat():
    allowed, msg = check_limit(current_user, 'ai_requests')
    if not allowed:
        return jsonify({'success': False, 'error': msg}), 403

    data = request.get_json() or {}
    message = data.get('message', '').strip()
    if not message:
        return jsonify({'success': False, 'error': 'Mensagem não pode estar vazia.'}), 400

    conversation_id = data.get('conversation_id')
    ok, msg, result = chat(current_user, conversation_id, message)
    status = 200 if ok else 400
    return jsonify({'success': ok, 'message': msg, 'data': result}), status


@ai_bp.route('/api/ai/conversations')
@login_required
def api_conversations():
    data = list_conversations(current_user.id)
    return jsonify({'success': True, 'data': data})


@ai_bp.route('/api/ai/conversations/<int:conv_id>', methods=['GET'])
@login_required
def api_get_conversation(conv_id):
    conv = get_conversation(current_user.id, conv_id)
    if not conv:
        return jsonify({'success': False, 'error': 'Conversa não encontrada.'}), 404
    return jsonify({'success': True, 'data': conv})


@ai_bp.route('/api/ai/conversations/<int:conv_id>', methods=['PATCH'])
@login_required
def api_rename_conversation(conv_id):
    data = request.get_json() or {}
    ok, msg = rename_conversation(current_user.id, conv_id, data.get('title', ''))
    return jsonify({'success': ok, 'message': msg}), (200 if ok else 400)


@ai_bp.route('/api/ai/conversations/<int:conv_id>', methods=['DELETE'])
@login_required
def api_delete_conversation(conv_id):
    ok, msg = delete_conversation(current_user.id, conv_id)
    return jsonify({'success': ok, 'message': msg}), (200 if ok else 404)
