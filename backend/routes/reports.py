"""
VEXX AI — Reports routes (PDF executive reports)
"""

import os
from flask import Blueprint, jsonify, send_file, abort, render_template
from flask_login import login_required, current_user
from services.report_service import generate_executive_pdf, list_user_reports

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/reports')
@login_required
def reports_page():
    return render_template('reports.html')


@reports_bp.route('/api/reports/list')
@login_required
def api_list():
    return jsonify({'success': True, 'data': list_user_reports(current_user.id)})


@reports_bp.route('/api/reports/generate', methods=['POST'])
@login_required
def api_generate():
    try:
        path, filename = generate_executive_pdf(current_user.id)
        from database.models import create_notification
        create_notification(
            current_user.id, 'success', '📊 Relatório executivo gerado',
            f'PDF disponível para download: {filename}', f'/api/reports/download/{filename}',
        )
        return jsonify({
            'success': True,
            'message': 'Relatório gerado!',
            'data': {
                'filename': filename,
                'download_url': f'/api/reports/download/{filename}',
            },
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/api/reports/download/<filename>')
@login_required
def api_download(filename):
    # Apenas arquivos do usuário (prefix-based isolation)
    if not filename.startswith(f'executivo_{current_user.id}_') or not filename.endswith('.pdf'):
        abort(403)

    reports_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'database', 'reports',
    )
    path = os.path.join(reports_dir, filename)
    if not os.path.isfile(path):
        abort(404)
    return send_file(path, as_attachment=True, download_name=filename, mimetype='application/pdf')


@reports_bp.route('/api/reports/<filename>', methods=['DELETE'])
@login_required
def api_delete(filename):
    if not filename.startswith(f'executivo_{current_user.id}_'):
        abort(403)
    reports_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'database', 'reports',
    )
    path = os.path.join(reports_dir, filename)
    if os.path.isfile(path):
        os.remove(path)
    return jsonify({'success': True, 'message': 'Relatório removido.'})
