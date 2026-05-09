"""
VEXX AI — Tokens descartáveis para email verification e password reset.

O token é gerado aleatoriamente e armazenamos apenas seu hash SHA-256 no
banco — assim, mesmo um dump do DB não compromete os tokens. O hash é
verificado contra hash do token recebido na URL.
"""

import secrets
import hashlib
from datetime import datetime, timedelta

from database.db import db
from database.models import AuthToken, User


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_token(user_id: int, purpose: str, hours_valid: int = 24) -> str:
    """Cria token e retorna o valor RAW (envie por email; ele não fica no DB)."""
    raw = secrets.token_urlsafe(32)
    token = AuthToken(
        user_id=user_id,
        token_hash=_hash_token(raw),
        purpose=purpose,
        expires_at=datetime.utcnow() + timedelta(hours=hours_valid),
    )
    db.session.add(token)
    db.session.commit()
    return raw


def consume_token(raw: str, purpose: str) -> User | None:
    """Valida + consome o token. Retorna o User se válido, None caso contrário."""
    token_hash = _hash_token(raw)
    token = AuthToken.query.filter_by(token_hash=token_hash, purpose=purpose).first()
    if not token or not token.is_valid:
        return None

    user = User.query.get(token.user_id)
    if not user:
        return None

    token.consumed_at = datetime.utcnow()
    db.session.commit()
    return user


def revoke_user_tokens(user_id: int, purpose: str = None):
    """Invalida todos os tokens não consumidos do usuário (ex: ao trocar senha)."""
    q = AuthToken.query.filter_by(user_id=user_id, consumed_at=None)
    if purpose:
        q = q.filter_by(purpose=purpose)
    q.update({'consumed_at': datetime.utcnow()})
    db.session.commit()
