from database.db import db
from database.models import Contact, Lead
from utils.validators import sanitize_string, validate_required


def list_contacts(user_id: int, search: str = '', status: str = '') -> list:
    q = Contact.query.filter_by(user_id=user_id)
    if search:
        q = q.filter(
            (Contact.name.ilike(f'%{search}%')) |
            (Contact.email.ilike(f'%{search}%')) |
            (Contact.company.ilike(f'%{search}%'))
        )
    if status:
        q = q.filter_by(status=status)
    return [c.to_dict() for c in q.order_by(Contact.created_at.desc()).all()]


def create_contact(user_id: int, data: dict) -> tuple[bool, str, dict | None]:
    ok, msg = validate_required(data, ['name'])
    if not ok:
        return False, msg, None

    contact = Contact(
        user_id=user_id,
        name=sanitize_string(data['name'], 100),
        email=sanitize_string(data.get('email', ''), 120),
        phone=sanitize_string(data.get('phone', ''), 30),
        company=sanitize_string(data.get('company', ''), 100),
        position=sanitize_string(data.get('position', ''), 100),
        status=data.get('status', 'active'),
        notes=sanitize_string(data.get('notes', ''), 2000),
        tags=sanitize_string(data.get('tags', ''), 300),
    )
    db.session.add(contact)
    db.session.commit()

    # Dispara automações com trigger='new_contact'
    try:
        from services.automation_service import trigger_event
        trigger_event(user_id, 'new_contact', {'contact': contact.to_dict()})
    except Exception:
        pass

    return True, 'Contato criado.', contact.to_dict()


def update_contact(user_id: int, contact_id: int, data: dict) -> tuple[bool, str]:
    contact = Contact.query.filter_by(id=contact_id, user_id=user_id).first()
    if not contact:
        return False, 'Contato não encontrado.'

    for field in ['name', 'email', 'phone', 'company', 'position', 'status', 'notes', 'tags']:
        if field in data:
            setattr(contact, field, sanitize_string(str(data[field]), 300))
    db.session.commit()
    return True, 'Contato atualizado.'


def delete_contact(user_id: int, contact_id: int) -> tuple[bool, str]:
    contact = Contact.query.filter_by(id=contact_id, user_id=user_id).first()
    if not contact:
        return False, 'Contato não encontrado.'
    db.session.delete(contact)
    db.session.commit()
    return True, 'Contato removido.'


def list_leads(user_id: int, stage: str = '') -> list:
    q = Lead.query.filter_by(user_id=user_id)
    if stage:
        q = q.filter_by(stage=stage)
    return [l.to_dict() for l in q.order_by(Lead.created_at.desc()).all()]


def create_lead(user_id: int, data: dict) -> tuple[bool, str, dict | None]:
    ok, msg = validate_required(data, ['title'])
    if not ok:
        return False, msg, None

    lead = Lead(
        user_id=user_id,
        title=sanitize_string(data['title'], 200),
        stage=data.get('stage', 'prospect'),
        value=float(data.get('value', 0)),
        probability=int(data.get('probability', 10)),
        notes=sanitize_string(data.get('notes', ''), 2000),
        contact_id=data.get('contact_id'),
    )
    db.session.add(lead)
    db.session.commit()

    try:
        from services.automation_service import trigger_event
        trigger_event(user_id, 'new_lead', {'lead': lead.to_dict()})
    except Exception:
        pass

    return True, 'Lead criado.', lead.to_dict()


def update_lead_stage(user_id: int, lead_id: int, stage: str) -> tuple[bool, str]:
    lead = Lead.query.filter_by(id=lead_id, user_id=user_id).first()
    if not lead:
        return False, 'Lead não encontrado.'
    if stage not in Lead.STAGES:
        return False, 'Estágio inválido.'
    old_stage = lead.stage
    lead.stage = stage
    db.session.commit()

    try:
        from services.automation_service import trigger_event
        ctx = {'lead': lead.to_dict(), 'old_stage': old_stage, 'new_stage': stage}
        trigger_event(user_id, 'lead_stage_change', ctx)
        if stage == 'closed_won':
            trigger_event(user_id, 'lead_won', ctx)
        elif stage == 'closed_lost':
            trigger_event(user_id, 'lead_lost', ctx)
    except Exception:
        pass

    return True, 'Lead atualizado.'


def update_lead(user_id: int, lead_id: int, data: dict) -> tuple[bool, str]:
    lead = Lead.query.filter_by(id=lead_id, user_id=user_id).first()
    if not lead:
        return False, 'Lead não encontrado.'
    for field in ['title', 'stage', 'notes']:
        if field in data:
            setattr(lead, field, sanitize_string(str(data[field]), 300))
    if 'value' in data:
        lead.value = float(data['value'])
    if 'probability' in data:
        lead.probability = int(data['probability'])
    db.session.commit()
    return True, 'Lead atualizado.'


def delete_lead(user_id: int, lead_id: int) -> tuple[bool, str]:
    lead = Lead.query.filter_by(id=lead_id, user_id=user_id).first()
    if not lead:
        return False, 'Lead não encontrado.'
    db.session.delete(lead)
    db.session.commit()
    return True, 'Lead removido.'


def get_pipeline_summary(user_id: int) -> list:
    from sqlalchemy import func
    stages = Lead.STAGES
    result = []
    for stage in stages:
        leads = Lead.query.filter_by(user_id=user_id, stage=stage).all()
        total_value = sum(l.value for l in leads)
        result.append({
            'stage': stage,
            'count': len(leads),
            'total_value': round(total_value, 2),
        })
    return result
