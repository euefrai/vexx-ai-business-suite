import os
import hashlib
import secrets
import base64
from cryptography.fernet import Fernet, InvalidToken
from database.db import bcrypt


# ── Password hashing ─────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return bcrypt.generate_password_hash(password).decode('utf-8')


def check_password(password: str, hashed: str) -> bool:
    return bcrypt.check_password_hash(hashed, password)


# ── Random tokens ────────────────────────────────────────────────────────────
def generate_api_key() -> str:
    return f"vexx_{secrets.token_urlsafe(32)}"


def generate_invoice_number(user_id: int, sequence: int) -> str:
    return f"INV-{user_id:04d}-{sequence:05d}"


# ── Password strength ────────────────────────────────────────────────────────
COMMON_PASSWORDS = {
    '12345678', '123456789', 'password', 'password1', 'qwerty123',
    'abc12345', 'senha123', 'admin123', '123mudar', 'iloveyou',
    'password123', '11111111', '00000000', 'football', 'baseball',
}


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Retorna (ok, message). Política mínima:
       - 8+ caracteres
       - Pelo menos 1 letra
       - Pelo menos 1 número
       - Não pode ser uma das senhas comuns
    """
    if not password or len(password) < 8:
        return False, 'Senha deve ter no mínimo 8 caracteres.'
    if password.lower() in COMMON_PASSWORDS:
        return False, 'Esta senha é muito comum. Escolha algo mais único.'
    if not any(c.isalpha() for c in password):
        return False, 'A senha deve conter ao menos uma letra.'
    if not any(c.isdigit() for c in password):
        return False, 'A senha deve conter ao menos um número.'
    if len(password) > 128:
        return False, 'Senha excede o limite de 128 caracteres.'
    return True, 'OK'


def password_strength_score(password: str) -> int:
    """0-4. Usado pelo frontend para mostrar barra de força."""
    if not password:
        return 0
    score = 0
    if len(password) >= 8:  score += 1
    if len(password) >= 12: score += 1
    if any(c.isupper() for c in password) and any(c.islower() for c in password): score += 1
    if any(c.isdigit() for c in password): score += 1
    if any(not c.isalnum() for c in password): score += 1
    return min(score, 4)


# ── Symmetric encryption (Fernet) ────────────────────────────────────────────
# Derives a deterministic Fernet key from SECRET_KEY so encrypted data survives
# restarts. SECRET_KEY MUST be stable in production — rotating it breaks all
# previously-encrypted data.
def _fernet() -> Fernet:
    secret = os.environ.get('SECRET_KEY') or os.environ.get('VEXX_ENCRYPTION_KEY') or 'vexx-fallback-dev-only'
    digest = hashlib.sha256(secret.encode()).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_api_key(plaintext: str) -> str:
    """Encrypt an API key with Fernet (AES-128-CBC + HMAC-SHA256)."""
    if not plaintext:
        return ''
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_api_key(token: str) -> str:
    """Decrypt a Fernet token. Falls back to legacy base64 for old records."""
    if not token:
        return ''
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        # Backwards-compat: tokens stored under the old base64-only scheme.
        try:
            return base64.b64decode(token.encode()).decode()
        except Exception:
            return ''
