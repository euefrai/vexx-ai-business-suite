"""
VEXX AI — Pluggy client (Open Finance Brasil).
Docs: https://docs.pluggy.ai/

Como funciona:
  1. Usuário cadastra Pluggy Client ID/Secret em Integrações
  2. /api/automation/pluggy/connect-token  → cria connect_token (válido 30min)
  3. Frontend abre Pluggy Connect Widget passando esse token
  4. Após o usuário escolher banco, recebemos o `item_id` no callback
  5. /api/automation/pluggy/sync/<item_id>  → puxa contas e transações
"""

import requests
from datetime import datetime
from database.db import db
from database.models import Transaction
from services.integrations_service import get_credentials


PLUGGY_API = 'https://api.pluggy.ai'


def _get_api_key(user_id: int) -> str | None:
    """Obtém um API Key da Pluggy (válido 2h) usando client credentials."""
    creds = get_credentials(user_id, 'pluggy')
    if not creds:
        return None

    r = requests.post(f'{PLUGGY_API}/auth', json={
        'clientId':     creds['client_id'],
        'clientSecret': creds['client_secret'],
    }, timeout=10)
    if r.status_code >= 400:
        return None
    return r.json().get('apiKey')


def create_connect_token(user_id: int) -> tuple[bool, str, dict | None]:
    """Cria connect token para o widget Pluggy Connect."""
    api_key = _get_api_key(user_id)
    if not api_key:
        return False, 'Pluggy não conectado ou credenciais inválidas.', None

    r = requests.post(
        f'{PLUGGY_API}/connect_token',
        headers={'X-API-KEY': api_key, 'Content-Type': 'application/json'},
        json={'options': {'clientUserId': str(user_id)}},
        timeout=10,
    )
    if r.status_code >= 400:
        return False, f'Erro Pluggy: {r.text[:200]}', None
    return True, 'Token criado', r.json()


def list_items(user_id: int) -> list:
    """Lista bancos/items conectados deste usuário Pluggy."""
    api_key = _get_api_key(user_id)
    if not api_key:
        return []
    r = requests.get(
        f'{PLUGGY_API}/items',
        headers={'X-API-KEY': api_key},
        timeout=10,
    )
    if r.status_code >= 400:
        return []
    return r.json().get('results', [])


def sync_transactions(user_id: int, item_id: str, days: int = 30) -> tuple[bool, str, int]:
    """Importa transações dos últimos N dias como Transaction VEXX."""
    api_key = _get_api_key(user_id)
    if not api_key:
        return False, 'Pluggy não conectado.', 0

    # Lista contas do item
    r = requests.get(
        f'{PLUGGY_API}/accounts?itemId={item_id}',
        headers={'X-API-KEY': api_key},
        timeout=15,
    )
    if r.status_code >= 400:
        return False, f'Erro listando contas: {r.text[:150]}', 0

    accounts = r.json().get('results', [])
    imported = 0

    for acc in accounts:
        account_id = acc['id']
        r = requests.get(
            f'{PLUGGY_API}/transactions',
            headers={'X-API-KEY': api_key},
            params={'accountId': account_id, 'pageSize': 200},
            timeout=20,
        )
        if r.status_code >= 400:
            continue

        for tx in r.json().get('results', []):
            # Evita duplicatas usando descrição+data como chave fraca
            tx_date_str = tx.get('date', '')[:10]
            try:
                tx_date = datetime.fromisoformat(tx_date_str).date()
            except ValueError:
                continue

            description = (tx.get('description') or 'Pluggy import')[:200]
            amount = abs(float(tx.get('amount', 0)))
            tx_type = 'income' if tx.get('amount', 0) > 0 else 'expense'

            # Skip se já existe transação idêntica
            exists = Transaction.query.filter_by(
                user_id=user_id, type=tx_type,
                amount=amount, description=description, date=tx_date,
            ).first()
            if exists:
                continue

            db.session.add(Transaction(
                user_id=user_id,
                type=tx_type,
                amount=amount,
                description=description,
                category=tx.get('category', 'Banco') or 'Banco',
                date=tx_date,
            ))
            imported += 1

    db.session.commit()
    return True, f'{imported} transação(ões) importada(s).', imported
