import re


def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


def validate_password(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, 'A senha deve ter pelo menos 8 caracteres.'
    return True, ''


def validate_required(data: dict, fields: list) -> tuple[bool, str]:
    for field in fields:
        value = data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            return False, f'O campo "{field}" é obrigatório.'
    return True, ''


def sanitize_string(value: str, max_length: int = 500) -> str:
    if not value:
        return ''
    return str(value).strip()[:max_length]
