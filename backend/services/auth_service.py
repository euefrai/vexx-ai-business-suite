from database.db import db, bcrypt
from database.models import User
from utils.validators import validate_email, validate_required, sanitize_string
from utils.security import validate_password_strength


def register_user(data: dict) -> tuple[bool, str, User | None]:
    ok, msg = validate_required(data, ['first_name', 'last_name', 'email', 'password'])
    if not ok:
        return False, msg, None

    email = data['email'].strip().lower()
    if not validate_email(email):
        return False, 'E-mail inválido.', None

    ok, msg = validate_password_strength(data['password'])
    if not ok:
        return False, msg, None

    if User.query.filter_by(email=email).first():
        return False, 'Este e-mail já está cadastrado.', None

    user = User(
        first_name=sanitize_string(data['first_name'], 50),
        last_name=sanitize_string(data['last_name'], 50),
        email=email,
        password_hash=bcrypt.generate_password_hash(data['password']).decode('utf-8'),
        company=sanitize_string(data.get('company', ''), 100),
        plan=data.get('plan', 'free'),
        is_email_verified=False,
    )
    db.session.add(user)
    db.session.commit()

    # Dispara email de verificação (best-effort)
    try:
        from services.token_service import create_token
        from services.email_service import send_verification_email
        raw = create_token(user.id, 'email_verify', hours_valid=24)
        send_verification_email(user, raw)
    except Exception:
        pass  # registro continua mesmo se email falhar

    return True, 'Conta criada com sucesso! Verifique seu email para confirmar.', user


def authenticate_user(email: str, password: str) -> tuple[bool, str, User | None]:
    from datetime import datetime
    if not email or not password:
        return False, 'E-mail e senha são obrigatórios.', None

    user = User.query.filter_by(email=email.strip().lower()).first()
    if not user:
        return False, 'Credenciais inválidas.', None

    if not bcrypt.check_password_hash(user.password_hash, password):
        return False, 'Credenciais inválidas.', None

    if not user.is_active:
        return False, 'Conta desativada. Entre em contato com o suporte.', None

    user.last_login_at = datetime.utcnow()
    db.session.commit()
    return True, 'Login realizado com sucesso!', user


def update_profile(user: User, data: dict) -> tuple[bool, str]:
    if 'first_name' in data:
        user.first_name = sanitize_string(data['first_name'], 50)
    if 'last_name' in data:
        user.last_name = sanitize_string(data['last_name'], 50)
    if 'company' in data:
        user.company = sanitize_string(data['company'], 100)
    db.session.commit()
    return True, 'Perfil atualizado.'


def change_password(user: User, current_pw: str, new_pw: str) -> tuple[bool, str]:
    if not bcrypt.check_password_hash(user.password_hash, current_pw):
        return False, 'Senha atual incorreta.'
    ok, msg = validate_password_strength(new_pw)
    if not ok:
        return False, msg
    user.password_hash = bcrypt.generate_password_hash(new_pw).decode('utf-8')
    db.session.commit()
    return True, 'Senha alterada com sucesso.'
