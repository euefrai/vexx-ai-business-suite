"""
VEXX AI — Companies routes (multi-tenant workspace).
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from database.db import db
from database.models import Company, CompanyMember, User
from utils.validators import sanitize_string

companies_bp = Blueprint('companies', __name__)


@companies_bp.route('/api/companies')
@login_required
def api_my_companies():
    """Companies das quais o usuário é membro."""
    memberships = CompanyMember.query.filter_by(user_id=current_user.id).all()
    out = []
    for m in memberships:
        c = m.company
        if not c:
            continue
        d = c.to_dict()
        d['my_role'] = m.role
        out.append(d)

    # Se nada, mas o user tem string company nele, sugerimos criar
    return jsonify({'success': True, 'data': out, 'fallback_company_name': current_user.company})


@companies_bp.route('/api/companies', methods=['POST'])
@login_required
def api_create_company():
    data = request.get_json() or {}
    name = sanitize_string(data.get('name', '').strip(), 120)
    if not name:
        return jsonify({'success': False, 'error': 'Nome é obrigatório.'}), 400

    company = Company(
        owner_id=current_user.id,
        name=name,
        cnpj=sanitize_string(data.get('cnpj', ''), 20),
        industry=sanitize_string(data.get('industry', ''), 80),
        size=sanitize_string(data.get('size', ''), 20),
        timezone=sanitize_string(data.get('timezone', 'America/Sao_Paulo'), 40),
        currency=sanitize_string(data.get('currency', 'BRL'), 8),
        monthly_goal=float(data.get('monthly_goal', 0) or 0),
    )
    db.session.add(company)
    db.session.flush()

    # Criador entra como owner
    db.session.add(CompanyMember(
        company_id=company.id, user_id=current_user.id, role='owner', accepted=True,
    ))
    db.session.commit()
    return jsonify({'success': True, 'data': company.to_dict()}), 201


@companies_bp.route('/api/companies/<int:cid>', methods=['PUT'])
@login_required
def api_update_company(cid):
    membership = CompanyMember.query.filter_by(
        company_id=cid, user_id=current_user.id,
    ).first()
    if not membership or membership.role not in ('owner', 'admin'):
        return jsonify({'success': False, 'error': 'Sem permissão.'}), 403

    company = Company.query.get(cid)
    if not company:
        return jsonify({'success': False, 'error': 'Empresa não encontrada.'}), 404

    data = request.get_json() or {}
    for f in ['name', 'cnpj', 'industry', 'size', 'timezone', 'currency']:
        if f in data:
            setattr(company, f, sanitize_string(str(data[f]), 120))
    if 'monthly_goal' in data:
        try:
            company.monthly_goal = float(data['monthly_goal'])
        except ValueError:
            pass
    db.session.commit()
    return jsonify({'success': True, 'data': company.to_dict()})


@companies_bp.route('/api/companies/<int:cid>/members')
@login_required
def api_members(cid):
    me = CompanyMember.query.filter_by(company_id=cid, user_id=current_user.id).first()
    if not me:
        return jsonify({'success': False, 'error': 'Sem acesso.'}), 403

    members = CompanyMember.query.filter_by(company_id=cid).all()
    out = []
    for m in members:
        u = User.query.get(m.user_id)
        out.append({
            **m.to_dict(),
            'user_name': u.full_name if u else m.invited_email,
            'user_email': u.email if u else m.invited_email,
        })
    return jsonify({'success': True, 'data': out})


@companies_bp.route('/api/companies/<int:cid>/invite', methods=['POST'])
@login_required
def api_invite(cid):
    me = CompanyMember.query.filter_by(company_id=cid, user_id=current_user.id).first()
    if not me or me.role not in ('owner', 'admin'):
        return jsonify({'success': False, 'error': 'Sem permissão.'}), 403

    data = request.get_json() or {}
    email = (data.get('email', '') or '').strip().lower()
    role = data.get('role', 'member')
    if not email:
        return jsonify({'success': False, 'error': 'Email é obrigatório.'}), 400
    if role not in ('admin', 'member', 'viewer'):
        return jsonify({'success': False, 'error': 'Role inválido.'}), 400

    invited_user = User.query.filter_by(email=email).first()

    existing = CompanyMember.query.filter_by(
        company_id=cid, user_id=invited_user.id if invited_user else None,
    ).first() if invited_user else None
    if existing:
        return jsonify({'success': False, 'error': 'Já é membro.'}), 400

    member = CompanyMember(
        company_id=cid,
        user_id=invited_user.id if invited_user else None,
        role=role,
        invited_email=email,
        accepted=bool(invited_user),  # auto-aceita se já existe conta
    )
    db.session.add(member)
    db.session.commit()
    return jsonify({'success': True, 'message': f'Convite enviado para {email}.'})


@companies_bp.route('/api/companies/<int:cid>/members/<int:mid>', methods=['DELETE'])
@login_required
def api_remove_member(cid, mid):
    me = CompanyMember.query.filter_by(company_id=cid, user_id=current_user.id).first()
    if not me or me.role not in ('owner', 'admin'):
        return jsonify({'success': False, 'error': 'Sem permissão.'}), 403

    target = CompanyMember.query.filter_by(id=mid, company_id=cid).first()
    if not target:
        return jsonify({'success': False, 'error': 'Membro não encontrado.'}), 404
    if target.role == 'owner':
        return jsonify({'success': False, 'error': 'Não é possível remover o owner.'}), 400

    db.session.delete(target)
    db.session.commit()
    return jsonify({'success': True})
