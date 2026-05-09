# 🚀 VEXX AI Business Suite — Handoff de Sessão

**Última atualização:** 2026-05-07
**Próxima sessão:** continuar Bloco 3 do roadmap de produção

---

## 📁 Estrutura do projeto

```
VEXX-AI-Business-Suite/
├── backend/
│   ├── main.py                       # App factory Flask
│   ├── config.py                     # Dev / Production / Testing
│   ├── routes/
│   │   ├── auth.py                   # Login + register + email verify + password reset
│   │   ├── dashboard.py              # KPIs + notificações
│   │   ├── crm.py                    # Contatos + leads
│   │   ├── finance.py                # Transações + faturas
│   │   ├── automation.py             # Workflows + integrações + webhooks + Pluggy
│   │   ├── analytics.py              # Métricas
│   │   ├── ai.py                     # Chat IA + conversas
│   │   ├── settings.py               # Profile + API keys
│   │   ├── billing.py                # Plans + upgrade
│   │   ├── reports.py                # PDFs executivos
│   │   ├── oauth.py                  # Google OAuth flow
│   │   └── companies.py              # Multi-tenant base
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── token_service.py          # NOVO: tokens p/ email_verify + password_reset
│   │   ├── email_service.py          # NOVO: SMTP + console fallback
│   │   ├── dashboard_service.py
│   │   ├── crm_service.py
│   │   ├── finance_service.py
│   │   ├── automation_service.py     # 17 triggers + 14 actions + multi-step
│   │   ├── action_executor.py        # Email (SMTP/Gmail), WhatsApp, Telegram, Slack, Discord, webhook, etc.
│   │   ├── analytics_service.py
│   │   ├── ai_service.py             # OpenAI + Anthropic + DeepSeek
│   │   ├── settings_service.py
│   │   ├── billing_service.py
│   │   ├── report_service.py         # PDF ReportLab
│   │   ├── oauth_service.py          # Google OAuth
│   │   ├── pluggy_service.py         # Open Finance Brasil
│   │   └── integrations_service.py   # 18 providers no marketplace
│   ├── database/
│   │   ├── db.py                     # SQLAlchemy + Login + Bcrypt + CSRF + Limiter + Migrate
│   │   ├── models.py                 # 12 modelos
│   │   ├── vexx.db                   # SQLite (dev)
│   │   ├── migrations/               # Alembic
│   │   ├── reports/                  # PDFs gerados
│   │   └── sent_emails/              # Emails de dev (HTML)
│   └── utils/
│       ├── security.py               # Fernet + bcrypt + password strength
│       ├── permissions.py            # Plan limits
│       └── validators.py
├── frontend/
│   ├── index.html                    # Landing
│   ├── login.html                    # Form + JS click handler + fallback POST
│   ├── register.html                 # Form + medidor de força + fallback POST
│   ├── forgot_password.html          # NOVO
│   ├── reset_password.html           # NOVO
│   ├── dashboard.html                # KPIs + AI orb + chart
│   ├── crm.html                      # Tabela contatos + kanban leads
│   ├── finance.html                  # KPIs + transações + faturas
│   ├── automation.html               # 6 abas (Workflows, Integrações, Templates, Sugestões, Logs, Webhooks)
│   ├── analytics.html
│   ├── ai_assistant.html             # Chat com sidebar de conversas
│   ├── settings.html                 # API keys
│   ├── billing.html
│   ├── pricing.html
│   ├── reports.html                  # Histórico de PDFs
│   ├── css/                          # global, sidebar, widgets, dashboard, responsive, auth
│   └── js/                           # api, auth-check, sidebar, page-shell, dashboard, crm, finance, ai, automation, analytics, billing
├── .env                              # SECRET_KEY, JWT_SECRET_KEY, FLASK_ENV (vazio: GOOGLE_CLIENT_*, SMTP_*, SENTRY_DSN, DATABASE_URL)
├── .vscode/
│   ├── launch.json                   # F5 = run/debug
│   └── tasks.json                    # Iniciar/matar servidores
└── requirements.txt
```

---

## 🔐 Credenciais demo

| Email | Senha | Plano |
|---|---|---|
| `bsdfai1001@gmail.com` | `@Eujhonny1334` | Enterprise |
| `admin@vexx.ai` | `vexx2026` | Pro (seed legado) |

---

## 🛠️ Stack técnica

**Backend:** Flask 3 + SQLAlchemy + Flask-Login + Flask-WTF (CSRF) + Flask-Limiter + Flask-Migrate (Alembic) + Flask-Bcrypt + Flask-JWT
**Crypto:** Fernet (AES-128-CBC + HMAC) — derivado de SECRET_KEY
**DB:** SQLite (dev), PostgreSQL ready (psycopg2-binary instalado)
**Email:** SMTP real ou console+arquivo HTML em dev
**PDF:** ReportLab Platypus
**OAuth:** Authlib (Google)
**Open Finance:** Pluggy SDK manual
**AI:** OpenAI GPT-4o-mini, Anthropic Claude Haiku 4.5, DeepSeek V3
**Frontend:** HTML/CSS/JS vanilla + Lucide icons + Chart.js 4.4
**Observability:** Sentry SDK opt-in via SENTRY_DSN

---

## ✅ O QUE JÁ FOI ENTREGUE

### Bloco 1 — Segurança crítica (CONCLUÍDO)
- [x] CSRF protection (Flask-WTF) em todos POST/PUT/PATCH/DELETE
- [x] Rate limiting (Flask-Limiter): login 10/min, register 5/h, AI chat 30/min, password 5/min
- [x] Senha forte (8+ chars, letra+número, lista de comuns proibidas, medidor visual)
- [x] Cookies seguros (HttpOnly, SameSite=Lax dev/Strict prod, Secure em prod)
- [x] Sentry init opt-in
- [x] /health endpoint
- [x] /api/csrf endpoint p/ refresh
- [x] `<meta name="csrf-token">` auto-injetado em qualquer HTML via `after_request`
- [x] Smoke test 5/5 passou

### Bloco 2 — Migrations + DB de produção + Auth flows (CONCLUÍDO)
- [x] Flask-Migrate (Alembic) — `flask db migrate` / `flask db upgrade`
- [x] PostgreSQL pronto (driver instalado, DATABASE_URL respeitado)
- [x] Modelo `AuthToken` (token_hash SHA-256, purpose, expires_at)
- [x] Modelo User estendido: `is_email_verified`, `last_login_at`
- [x] `token_service.py` (create / consume / revoke)
- [x] `email_service.py` (SMTP real ou console fallback com HTML)
- [x] Email verification flow (`/verify-email?token=...`)
- [x] Password reset flow (`/forgot-password` + `/reset-password`)
- [x] Frontend `forgot_password.html` + `reset_password.html`
- [x] Templates HTML profissionais para emails

### Auditoria pós-Bloco 2 (CONCLUÍDA — fixes aplicados)
- [x] Debug bar de login só ativa com `?debug=1`
- [x] Register com fallback HTML (POST /register)
- [x] `/api/auth/login` SEMPRE retorna JSON (nunca HTML)
- [x] Imports inúteis removidos
- [x] `render_template_str_safe` removido (era wrapper desnecessário)
- [x] Smoke test 5/5 passou

---

## 📋 PRÓXIMO BLOCO (não iniciado)

### Bloco 3 — Pagamentos + 2FA + Validação + Workers
1. **Stripe Subscriptions reais** (Free → Pro → Enterprise)
   - Stripe Customer + Subscription criados no upgrade
   - Webhook `/webhooks/stripe/<user_id>` com HMAC validation
   - Trial de 14 dias com `trial_ends_at` no User
   - Downgrade automático ao expirar
2. **2FA TOTP** (Google Authenticator / Authy)
   - Library `pyotp`
   - Endpoint `/api/auth/2fa/enable` retorna QR Code
   - Validação adicional no login
3. **Validation schemas** (Marshmallow ou Pydantic)
   - Substituir `request.get_json() or {}` por schemas formais
   - Mensagens de erro padronizadas
4. **Background workers** (Celery + Redis)
   - Substituir APScheduler in-process
   - Queues: emails, sync bancário, PDFs, automações scheduled
5. **Pagination universal** em todos endpoints de listagem
   - `?page=1&per_page=50` no CRM, Finance, etc.
6. **Multi-tenant queries reais**
   - Refatorar queries para `company_id` quando User.company_id existir
   - `current_user.active_company_id` no contexto

---

## 🔧 Como rodar

```bash
cd C:\Users\efrai\Documents\VEXX-AI-Business-Suite
pip install -r requirements.txt
python backend/main.py
# Acessar: http://localhost:5000/login
```

VS Code: F5 → "VEXX AI — Dev (Flask)" (debug ativo)

Matar servidores zumbis (problema recorrente em Windows):
```bash
taskkill /F /IM python.exe
```

---

## ⚠️ GARGALOS CONHECIDOS

1. **APScheduler in-process** — workflows scheduled morrem se servidor reinicia. Resolver na Bloco 3.
2. **Múltiplas instâncias Flask zumbis em Windows** — `pkill` não mata sempre, precisa `taskkill /F /IM python.exe`. Mitigado com tasks no VS Code.
3. **Multi-tenant não enforçado** — modelos Company existem mas queries ainda usam `user_id`. Refatorar na Bloco 3.
4. **Sem testes automatizados** — pytest planejado mas não implementado.
5. **OAuth Google requer `GOOGLE_CLIENT_ID/SECRET` no .env** — sem isso, abre modal manual.

---

## 🔑 Variáveis de ambiente (.env)

```bash
# OBRIGATÓRIAS em produção (FLASK_ENV=production força)
SECRET_KEY=<gerar com `python -c "import secrets; print(secrets.token_urlsafe(32))"`>
JWT_SECRET_KEY=<idem>

# OPCIONAIS
FLASK_ENV=development                    # ou production
DATABASE_URL=postgresql://user:pw@host/db   # default: SQLite local

# Email (sem isso, salva em backend/database/sent_emails/)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG.xxx
SMTP_FROM=noreply@vexx.ai
PUBLIC_BASE_URL=https://app.vexx.ai

# Google OAuth (sem isso, fallback manual)
GOOGLE_CLIENT_ID=...apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-...

# Sentry (sem isso, sem error tracking)
SENTRY_DSN=https://xxx@sentry.io/yyy
```

---

## 📊 Modelos do DB (12)

`User`, `Contact`, `Lead`, `Transaction`, `Invoice`, `Automation`, `AutomationLog`,
`Integration`, `AIConversation`, `APIKey`, `Notification`, `AuthToken`,
`Company`, `CompanyMember`

---

## 🎯 Funcionalidades por área

| Área | Status |
|---|---|
| Login / Register / Logout | ✅ Production-ready (CSRF, rate limit, senha forte) |
| Email verification | ✅ Backend + frontend, SMTP opt-in |
| Password reset | ✅ Backend + frontend, link expira em 1h |
| Dashboard (KPIs + chart + AI orb) | ✅ |
| CRM (contatos + leads kanban) | ✅ Multi-step move + autocompletar |
| Financeiro (transações + faturas) | ✅ |
| AI Assistant (chat + conversas) | ✅ Delete + rename + scroll fix |
| Automation Hub (6 abas) | ✅ 18 providers, 17 triggers, 14 actions, multi-step |
| Analytics (4 charts) | ✅ |
| Reports (PDF executivo) | ✅ ReportLab profissional |
| Settings (profile + API keys) | ✅ Fernet encryption |
| Billing (3 planos + upgrade) | ⚠️ Funciona mas SEM Stripe real (Bloco 3) |
| Pricing (landing pública) | ✅ |
| Notifications (sino topbar) | ✅ |
| Integrações (Gmail OAuth, Pluggy banking) | ✅ Framework + endpoints |
| Webhooks externos | ✅ `/webhooks/<user_id>/<event>` |
| 2FA | ❌ Bloco 3 |
| Stripe pagamento real | ❌ Bloco 3 |
| Background workers (Celery) | ❌ Bloco 3 |
| Pagination | ❌ Bloco 3 |
| Tests pytest | ❌ Backlog |

---

## 🔥 PROMPT PARA RETOMAR

Use este prompt no novo chat:

> Estou continuando o projeto VEXX AI Business Suite em
> `C:\Users\efrai\Documents\VEXX-AI-Business-Suite`. Leia
> `.context/SESSION_HANDOFF.md` para contexto completo. Estamos
> prontos para o **Bloco 3** do roadmap: Stripe Subscriptions reais,
> 2FA TOTP, Validation Schemas, Background workers (Celery+Redis),
> Pagination universal e Multi-tenant queries. Comece pelo item de
> maior impacto: **Stripe Subscriptions ponta-a-ponta** (Customer +
> Subscription + webhook HMAC + trial 14d + downgrade automático).
