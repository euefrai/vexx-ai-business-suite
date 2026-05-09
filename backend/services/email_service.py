"""
VEXX AI — Email service (transactional emails).

Em dev (sem SMTP_HOST configurado): imprime no console + salva em
backend/database/sent_emails/ para debug.

Em produção: envia via SMTP real configurado em .env:
  SMTP_HOST=smtp.sendgrid.net
  SMTP_PORT=587
  SMTP_USER=apikey
  SMTP_PASSWORD=...
  SMTP_FROM=noreply@vexx.ai
  PUBLIC_BASE_URL=https://app.vexx.ai
"""

import os
import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


log = logging.getLogger('vexx.email')


def _config(key: str, default: str = '') -> str:
    return os.environ.get(key, default)


def public_base_url() -> str:
    return _config('PUBLIC_BASE_URL', 'http://localhost:5000').rstrip('/')


def is_smtp_configured() -> bool:
    return all([_config('SMTP_HOST'), _config('SMTP_USER'), _config('SMTP_PASSWORD')])


def send_email(to_addr: str, subject: str, html_body: str, text_body: str = '') -> tuple[bool, str]:
    """Envia email. Retorna (ok, info)."""
    if is_smtp_configured():
        return _send_smtp(to_addr, subject, html_body, text_body)
    return _send_console(to_addr, subject, html_body, text_body)


def _send_smtp(to_addr, subject, html_body, text_body) -> tuple[bool, str]:
    host = _config('SMTP_HOST')
    port = int(_config('SMTP_PORT', '587'))
    user = _config('SMTP_USER')
    pw   = _config('SMTP_PASSWORD')
    sender = _config('SMTP_FROM', user)

    msg = MIMEMultipart('alternative')
    msg['From']    = sender
    msg['To']      = to_addr
    msg['Subject'] = subject
    if text_body:
        msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    try:
        with smtplib.SMTP(host, port, timeout=15) as s:
            s.starttls()
            s.login(user, pw)
            s.sendmail(sender, [to_addr], msg.as_string())
        log.info(f'Email SMTP enviado para {to_addr}')
        return True, f'Enviado via SMTP para {to_addr}'
    except Exception as e:
        log.exception(f'SMTP falhou para {to_addr}')
        return False, f'SMTP falhou: {e}'


def _send_console(to_addr, subject, html_body, text_body) -> tuple[bool, str]:
    """Em dev: imprime no console + salva arquivo HTML para abrir no browser."""
    out_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'database', 'sent_emails',
    )
    os.makedirs(out_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    fname = f"{timestamp}_{to_addr.replace('@', '_at_')}.html"
    fpath = os.path.join(out_dir, fname)
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(f"<!-- VEXX dev email -->\n<!-- to: {to_addr}\n     subject: {subject} -->\n{html_body}")

    msg = (
        '\n' + '=' * 70 + '\n'
        f'[DEV EMAIL] To: {to_addr}\n'
        f'   Subject: {subject}\n'
        f'   Salvo em: {fpath}\n'
        + '=' * 70 + '\n'
    )
    # Fallback seguro p/ Windows cp1252
    try:
        print(msg)
    except UnicodeEncodeError:
        import sys
        sys.stdout.buffer.write(msg.encode('utf-8', errors='replace'))
        sys.stdout.buffer.write(b'\n')
    log.info(f'Dev email salvo: {fpath}')

    return True, f'Email salvo em {fpath} (modo dev — configure SMTP_* no .env para envio real)'


# ── Templates ────────────────────────────────────────────────────────────────

def send_verification_email(user, raw_token: str) -> tuple[bool, str]:
    url = f'{public_base_url()}/verify-email?token={raw_token}'
    html = f'''
<!DOCTYPE html><html><head><meta charset="utf-8"></head>
<body style="font-family: 'Inter', system-ui, sans-serif; background: #f5f7fb; padding: 40px 20px; margin: 0;">
  <div style="max-width: 520px; margin: 0 auto; background: white; border-radius: 14px; padding: 36px; box-shadow: 0 4px 20px rgba(0,0,0,0.05);">
    <div style="text-align: center; margin-bottom: 28px;">
      <div style="display: inline-block; width: 48px; height: 48px; background: linear-gradient(135deg, #6d28d9, #4338ca); border-radius: 12px; line-height: 48px; color: white; font-weight: 800; font-size: 22px;">V</div>
      <h2 style="color: #0c0c18; margin: 16px 0 4px; font-size: 22px;">Confirme seu email</h2>
    </div>
    <p style="color: #4b5563; font-size: 14.5px; line-height: 1.65;">
      Olá <strong>{user.first_name}</strong>, bem-vindo ao VEXX AI Business Suite!
    </p>
    <p style="color: #4b5563; font-size: 14.5px; line-height: 1.65;">
      Para ativar sua conta, confirme que esse email é seu clicando no botão abaixo:
    </p>
    <div style="text-align: center; margin: 28px 0;">
      <a href="{url}" style="display: inline-block; padding: 12px 28px; background: linear-gradient(135deg, #6d28d9, #4338ca); color: white; text-decoration: none; border-radius: 10px; font-weight: 600;">Confirmar email</a>
    </div>
    <p style="color: #9ca3af; font-size: 12px; line-height: 1.6;">
      Ou copie e cole no navegador:<br><span style="color: #6d28d9; word-break: break-all;">{url}</span>
    </p>
    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
    <p style="color: #9ca3af; font-size: 11.5px;">
      Este link expira em 24 horas. Se você não criou esta conta, ignore este email.
    </p>
  </div>
</body></html>'''
    text = (
        f'Olá {user.first_name},\n\n'
        f'Confirme seu email no VEXX AI clicando: {url}\n\n'
        f'Link válido por 24 horas.\n'
    )
    return send_email(user.email, 'Confirme seu email — VEXX AI', html, text)


def send_password_reset_email(user, raw_token: str) -> tuple[bool, str]:
    url = f'{public_base_url()}/reset-password?token={raw_token}'
    html = f'''
<!DOCTYPE html><html><head><meta charset="utf-8"></head>
<body style="font-family: 'Inter', system-ui, sans-serif; background: #f5f7fb; padding: 40px 20px; margin: 0;">
  <div style="max-width: 520px; margin: 0 auto; background: white; border-radius: 14px; padding: 36px; box-shadow: 0 4px 20px rgba(0,0,0,0.05);">
    <div style="text-align: center; margin-bottom: 28px;">
      <div style="display: inline-block; width: 48px; height: 48px; background: linear-gradient(135deg, #6d28d9, #4338ca); border-radius: 12px; line-height: 48px; color: white; font-weight: 800; font-size: 22px;">V</div>
      <h2 style="color: #0c0c18; margin: 16px 0 4px; font-size: 22px;">Redefinir senha</h2>
    </div>
    <p style="color: #4b5563; font-size: 14.5px; line-height: 1.65;">
      Olá <strong>{user.first_name}</strong>,
    </p>
    <p style="color: #4b5563; font-size: 14.5px; line-height: 1.65;">
      Recebemos uma solicitação de redefinição de senha. Se foi você, clique abaixo:
    </p>
    <div style="text-align: center; margin: 28px 0;">
      <a href="{url}" style="display: inline-block; padding: 12px 28px; background: linear-gradient(135deg, #6d28d9, #4338ca); color: white; text-decoration: none; border-radius: 10px; font-weight: 600;">Redefinir senha</a>
    </div>
    <p style="color: #9ca3af; font-size: 12px; line-height: 1.6;">
      Link direto:<br><span style="color: #6d28d9; word-break: break-all;">{url}</span>
    </p>
    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
    <p style="color: #9ca3af; font-size: 11.5px;">
      Link expira em 1 hora. Se você não solicitou, ignore este email — sua senha permanece a mesma.
    </p>
  </div>
</body></html>'''
    text = (
        f'Olá {user.first_name},\n\n'
        f'Para redefinir sua senha: {url}\n\n'
        f'Link válido por 1 hora.\n'
    )
    return send_email(user.email, 'Redefinir senha — VEXX AI', html, text)
