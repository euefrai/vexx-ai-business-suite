"""
VEXX AI — OAuth flow service (Google).

Como usar:
  1. Criar OAuth Client ID em https://console.cloud.google.com/apis/credentials
     - Tipo: Web application
     - Authorized redirect URI: http://localhost:5000/oauth/google/callback
  2. Adicionar ao .env:
        GOOGLE_CLIENT_ID=...
        GOOGLE_CLIENT_SECRET=...
  3. Frontend chama /oauth/google/authorize?provider=gmail
  4. Usuário autoriza no Google e volta para /oauth/google/callback
     que troca o code por tokens e salva como Integration cifrada.
"""

import os
import secrets
import json
import requests
from urllib.parse import urlencode
from datetime import datetime, timedelta

from database.db import db
from database.models import Integration
from utils.security import encrypt_api_key


# Mapeamento provider VEXX → escopos Google
PROVIDER_SCOPES = {
    'gmail': [
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/userinfo.email',
    ],
    'google_sheets': [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/userinfo.email',
    ],
    'google_calendar': [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/userinfo.email',
    ],
}

GOOGLE_AUTH_URL  = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO  = 'https://www.googleapis.com/oauth2/v2/userinfo'


def _client_id():
    return os.environ.get('GOOGLE_CLIENT_ID', '')


def _client_secret():
    return os.environ.get('GOOGLE_CLIENT_SECRET', '')


def _redirect_uri(base_url: str) -> str:
    # Prioriza variável de ambiente para controle explícito
    override = os.environ.get('OAUTH_REDIRECT_BASE', '').strip().rstrip('/')
    if override:
        return f'{override}/oauth/google/callback'
    return f'{base_url.rstrip("/")}/oauth/google/callback'


def get_expected_redirect_uri() -> str:
    """Retorna a URI que deve ser configurada no Google Cloud Console."""
    override = os.environ.get('OAUTH_REDIRECT_BASE', '').strip().rstrip('/')
    base = override or 'http://localhost:5000'
    return f'{base}/oauth/google/callback'


def is_configured() -> bool:
    return bool(_client_id() and _client_secret())


def build_authorize_url(user_id: int, provider: str, base_url: str) -> tuple[str | None, str | None]:
    """Retorna (url, state). State é assinado para validação no callback."""
    scopes = PROVIDER_SCOPES.get(provider)
    if not scopes:
        return None, None

    if not is_configured():
        return None, None

    state = secrets.token_urlsafe(24)
    state_payload = f'{user_id}:{provider}:{state}'

    params = {
        'client_id':     _client_id(),
        'redirect_uri':  _redirect_uri(base_url),
        'response_type': 'code',
        'scope':         ' '.join(scopes),
        'access_type':   'offline',
        'prompt':        'consent',  # força receber refresh_token toda vez
        'state':         state_payload,
    }
    return f'{GOOGLE_AUTH_URL}?{urlencode(params)}', state_payload


def exchange_code(code: str, base_url: str) -> dict:
    """Troca authorization code por tokens."""
    r = requests.post(GOOGLE_TOKEN_URL, data={
        'code':          code,
        'client_id':     _client_id(),
        'client_secret': _client_secret(),
        'redirect_uri':  _redirect_uri(base_url),
        'grant_type':    'authorization_code',
    }, timeout=15)
    r.raise_for_status()
    return r.json()


def fetch_userinfo(access_token: str) -> dict:
    r = requests.get(GOOGLE_USERINFO,
                     headers={'Authorization': f'Bearer {access_token}'},
                     timeout=10)
    r.raise_for_status()
    return r.json()


def save_oauth_integration(user_id: int, provider: str, tokens: dict, userinfo: dict) -> Integration:
    """Salva tokens recebidos como Integration cifrada."""
    creds = {
        'access_token':  tokens.get('access_token'),
        'refresh_token': tokens.get('refresh_token'),
        'expires_at':    (datetime.utcnow() + timedelta(seconds=tokens.get('expires_in', 3600))).isoformat(),
        'token_type':    tokens.get('token_type', 'Bearer'),
        'scope':         tokens.get('scope', ''),
        'from_email':    userinfo.get('email', ''),
    }

    integ = Integration.query.filter_by(user_id=user_id, provider=provider).first()
    if integ:
        integ.credentials_encrypted = encrypt_api_key(json.dumps(creds))
        integ.status = 'connected'
        integ.last_sync_at = datetime.utcnow()
        integ.last_error = None
        integ.name = userinfo.get('email') or integ.name
    else:
        integ = Integration(
            user_id=user_id, provider=provider,
            name=userinfo.get('email', provider),
            auth_type='oauth',
            credentials_encrypted=encrypt_api_key(json.dumps(creds)),
            config=json.dumps({}),
            status='connected',
        )
        db.session.add(integ)

    db.session.commit()
    return integ


def refresh_token(user_id: int, provider: str) -> bool:
    """Renova access_token usando refresh_token salvo."""
    from services.integrations_service import get_credentials
    creds = get_credentials(user_id, provider)
    if not creds or not creds.get('refresh_token'):
        return False

    r = requests.post(GOOGLE_TOKEN_URL, data={
        'refresh_token': creds['refresh_token'],
        'client_id':     _client_id(),
        'client_secret': _client_secret(),
        'grant_type':    'refresh_token',
    }, timeout=15)
    if r.status_code >= 400:
        return False

    tokens = r.json()
    creds['access_token'] = tokens.get('access_token')
    creds['expires_at']   = (datetime.utcnow() +
                             timedelta(seconds=tokens.get('expires_in', 3600))).isoformat()

    integ = Integration.query.filter_by(user_id=user_id, provider=provider).first()
    if integ:
        integ.credentials_encrypted = encrypt_api_key(json.dumps(creds))
        integ.last_sync_at = datetime.utcnow()
        db.session.commit()
        return True
    return False
