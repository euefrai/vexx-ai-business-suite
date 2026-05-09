from datetime import datetime, date
from typing import Any


def success(data: Any = None, message: str = 'OK', status: int = 200):
    from flask import jsonify
    payload = {'success': True, 'message': message}
    if data is not None:
        payload['data'] = data
    return jsonify(payload), status


def error(message: str, status: int = 400, details: Any = None):
    from flask import jsonify
    payload = {'success': False, 'error': message}
    if details:
        payload['details'] = details
    return jsonify(payload), status


def format_currency(value: float, symbol: str = 'R$') -> str:
    return f"{symbol} {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def month_range(year: int, month: int) -> tuple:
    from calendar import monthrange
    first = date(year, month, 1)
    last = date(year, month, monthrange(year, month)[1])
    return first, last


def current_month_range() -> tuple:
    today = date.today()
    return month_range(today.year, today.month)


def percentage_change(current: float, previous: float) -> float:
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)
