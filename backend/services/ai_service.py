"""
VEXX AI — AI Service (contextual, business-aware)

Conecta a IA aos dados reais do sistema. Detecta intents nas perguntas e
injeta contexto empresarial relevante antes de chamar o provedor externo.
Quando não há API key configurada, gera respostas reais a partir dos dados.
"""
import json
import requests
from datetime import datetime
from database.db import db
from database.models import AIConversation, APIKey, User
from utils.security import decrypt_api_key
from services.business_context import (
    get_business_summary, get_profit_margin, get_monthly_revenue,
    get_monthly_expenses, get_pipeline_summary, get_conversion_rate,
    get_growth_metrics, get_new_leads, get_quarterly_revenue,
    get_pending_invoices, get_automation_stats, get_top_revenue_categories,
    get_top_leads_by_value, get_contacts_count,
)


# ──────────────────────────────────────────────────────────────────────────────
# System prompt
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT_BASE = """Você é o **VEXX AI Business Assistant**, um diretor operacional inteligente integrado à plataforma VEXX AI Business Suite.

REGRAS FUNDAMENTAIS:
1. SEMPRE priorize os dados reais da empresa (fornecidos no bloco BUSINESS_CONTEXT) antes de respostas genéricas.
2. Ao responder sobre finanças, clientes, leads, automações ou métricas, use os números reais — nunca invente nem use exemplos fictícios.
3. Forneça insights estratégicos e recomendações práticas baseadas nos dados.
4. Se uma métrica solicitada não estiver no contexto, diga claramente que precisa ser registrada na plataforma.
5. Responda em português brasileiro, de forma profissional, objetiva e executiva.
6. Use formatação markdown (negrito, listas) para destacar números e conclusões.
7. Mantenha respostas concisas — gestores valorizam decisões rápidas baseadas em fatos."""


# ──────────────────────────────────────────────────────────────────────────────
# Intent detection
# ──────────────────────────────────────────────────────────────────────────────

INTENT_KEYWORDS = {
    'finance': [
        'lucro', 'margem', 'receita', 'faturamento', 'fatur', 'despesa', 'gasto',
        'custo', 'caixa', 'saldo', 'financeiro', 'rentabilidade', 'breakeven',
        'ebitda', 'fluxo', 'roi', 'invest',
    ],
    'crm': [
        'cliente', 'contato', 'lead', 'crm', 'pipeline', 'funil', 'vendas',
        'conversão', 'oportunidade', 'prospect', 'qualific', 'fechamento',
        'ganho', 'perdido', 'negociação',
    ],
    'growth': [
        'crescer', 'cresci', 'crescimento', 'expansão', 'escalar', 'aumentar',
        'evolução', 'tendência', 'projeção', 'meta', 'objetivo',
    ],
    'invoices': [
        'fatura', 'cobrança', 'inadimpl', 'pendência', 'pagamento', 'recebível',
    ],
    'automation': [
        'automação', 'automatizar', 'fluxo', 'automatização', 'workflow',
        'gatilho', 'trigger',
    ],
    'analytics': [
        'analytics', 'analise', 'análise', 'relatório', 'kpi', 'métrica',
        'dashboard', 'desempenho', 'performance',
    ],
    'summary': [
        'resumo', 'overview', 'visão geral', 'panorama', 'situação', 'como está',
        'como vai', 'estado do negócio', 'snapshot', 'executivo',
    ],
}


def detect_intents(message: str) -> list[str]:
    """Retorna lista de intents detectados na mensagem."""
    msg = message.lower()
    intents = []
    for intent, kws in INTENT_KEYWORDS.items():
        if any(kw in msg for kw in kws):
            intents.append(intent)
    return intents


# ──────────────────────────────────────────────────────────────────────────────
# Context builder
# ──────────────────────────────────────────────────────────────────────────────

def _build_context_block(user_id: int, intents: list[str]) -> str:
    """Monta o bloco BUSINESS_CONTEXT com base nos intents detectados."""
    summary = get_business_summary(user_id)

    # Sempre inclui finanças e CRM básicos — são as métricas mais consultadas.
    context = {
        'empresa': summary['company'],
        'plano': summary['plan'],
        'data_consulta': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'finance_resumo_mes_atual': summary['finance'],
        'crm_resumo': summary['crm'],
    }

    if 'growth' in intents:
        context['crescimento_30d'] = summary['growth']
    if 'automation' in intents:
        context['automacoes'] = summary['automations']
    if 'crm' in intents or 'finance' in intents:
        top_leads = get_top_leads_by_value(user_id, 5)
        if top_leads:
            context['top_leads_em_aberto'] = top_leads

    return json.dumps(context, ensure_ascii=False, indent=2)


def build_system_prompt(user: User, intents: list[str]) -> str:
    """Constrói o system prompt completo com contexto empresarial."""
    context_block = _build_context_block(user.id, intents)
    return f"""{SYSTEM_PROMPT_BASE}

═══════════════════════════════════════
BUSINESS_CONTEXT (dados reais do usuário {user.first_name} — atualizados agora)
═══════════════════════════════════════
{context_block}
═══════════════════════════════════════

Use os números acima para responder. Nunca os altere ou invente outros."""


# ──────────────────────────────────────────────────────────────────────────────
# Provider key + main chat
# ──────────────────────────────────────────────────────────────────────────────

def get_user_api_key(user_id: int) -> tuple[str | None, str | None]:
    key_obj = APIKey.query.filter_by(user_id=user_id, is_active=True).first()
    if not key_obj:
        return None, None
    try:
        return key_obj.provider, decrypt_api_key(key_obj.key_encrypted)
    except Exception:
        return None, None


def chat(user: User, conversation_id: int | None, message: str) -> tuple[bool, str, dict]:
    if conversation_id:
        conv = AIConversation.query.filter_by(id=conversation_id, user_id=user.id).first()
        if not conv:
            return False, 'Conversa não encontrada.', {}
    else:
        conv = AIConversation(
            user_id=user.id,
            title=message[:60] + '...' if len(message) > 60 else message,
        )
        db.session.add(conv)
        db.session.flush()

    messages = json.loads(conv.messages or '[]')
    messages.append({'role': 'user', 'content': message, 'time': datetime.utcnow().isoformat()})

    intents = detect_intents(message)
    provider, api_key = get_user_api_key(user.id)

    if api_key:
        system_prompt = build_system_prompt(user, intents)
        reply = _call_provider(provider, api_key, messages, system_prompt)
    else:
        # Sem API key — gera resposta a partir dos dados reais quando possível
        reply = _smart_fallback(message, user, intents)

    messages.append({'role': 'assistant', 'content': reply, 'time': datetime.utcnow().isoformat()})
    conv.messages = json.dumps(messages)
    conv.updated_at = datetime.utcnow()

    user.ai_usage_count += 1
    db.session.commit()

    return True, 'OK', {
        'conversation_id': conv.id,
        'reply': reply,
        'usage_count': user.ai_usage_count,
        'intents': intents,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Provider calls
# ──────────────────────────────────────────────────────────────────────────────

def _call_provider(provider: str, api_key: str, messages: list, system_prompt: str) -> str:
    clean = [{'role': m['role'], 'content': m['content']} for m in messages]
    try:
        if provider == 'anthropic':
            return _anthropic(api_key, clean, system_prompt)
        if provider == 'deepseek':
            return _deepseek(api_key, clean, system_prompt)
        return _openai(api_key, clean, system_prompt)
    except Exception as e:
        return f"⚠️ Erro ao conectar com o provedor de IA: {str(e)[:120]}\n\nVerifique sua API Key em **Configurações → API Keys**."


def _openai(api_key: str, messages: list, system_prompt: str) -> str:
    resp = requests.post(
        'https://api.openai.com/v1/chat/completions',
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        json={
            'model': 'gpt-4o-mini',
            'messages': [{'role': 'system', 'content': system_prompt}] + messages,
            'max_tokens': 1500, 'temperature': 0.7,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()['choices'][0]['message']['content']


def _anthropic(api_key: str, messages: list, system_prompt: str) -> str:
    resp = requests.post(
        'https://api.anthropic.com/v1/messages',
        headers={'x-api-key': api_key, 'anthropic-version': '2023-06-01', 'Content-Type': 'application/json'},
        json={
            'model': 'claude-haiku-4-5-20251001',
            'max_tokens': 1500,
            'system': system_prompt,
            'messages': messages,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()['content'][0]['text']


def _deepseek(api_key: str, messages: list, system_prompt: str) -> str:
    resp = requests.post(
        'https://api.deepseek.com/v1/chat/completions',
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        json={
            'model': 'deepseek-chat',
            'messages': [{'role': 'system', 'content': system_prompt}] + messages,
            'max_tokens': 1500,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()['choices'][0]['message']['content']


# ──────────────────────────────────────────────────────────────────────────────
# Smart fallback (sem API key) — responde com dados REAIS quando há intent
# ──────────────────────────────────────────────────────────────────────────────

def _fmt_brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def _smart_fallback(message: str, user: User, intents: list[str]) -> str:
    msg = message.lower()

    # 1. Margem de lucro / lucratividade
    if 'finance' in intents and any(w in msg for w in ['margem', 'lucro', 'lucrat', 'rentab']):
        m = get_profit_margin(user.id)
        if m['revenue'] == 0 and m['expenses'] == 0:
            return ("Ainda **não há transações** registradas neste mês. "
                    "Adicione receitas e despesas no módulo **Financeiro** para que eu calcule sua margem de lucro real.")
        msg_out = (
            f"📊 **Resultado do mês atual:**\n\n"
            f"- **Receita:** {_fmt_brl(m['revenue'])}\n"
            f"- **Despesas:** {_fmt_brl(m['expenses'])}\n"
            f"- **Lucro:** {_fmt_brl(m['profit'])}\n"
            f"- **Margem de lucro:** **{m['margin_pct']}%**\n\n"
        )
        if m['margin_pct'] < 10 and m['revenue'] > 0:
            msg_out += "⚠️ Margem abaixo de 10% — recomendo revisar custos operacionais ou aumentar precificação."
        elif m['margin_pct'] > 30:
            msg_out += "✅ Margem saudável (>30%). Bom momento para reinvestir em crescimento."
        return msg_out

    # 2. Receita mensal / faturamento
    if 'finance' in intents and any(w in msg for w in ['receita', 'faturamento', 'fatur']):
        rev = get_monthly_revenue(user.id)
        q = get_quarterly_revenue(user.id)
        cats = get_top_revenue_categories(user.id, 3)
        out = f"💰 **Faturamento atual:**\n\n- **Mês atual:** {_fmt_brl(rev)}\n- **Trimestre {q['quarter']}/{q['year']}:** {_fmt_brl(q['revenue'])}\n"
        if cats:
            out += "\n**Top categorias de receita:**\n" + "\n".join(f"- {c['category']}: {_fmt_brl(c['total'])}" for c in cats)
        return out

    # 3. Despesas
    if 'finance' in intents and any(w in msg for w in ['despesa', 'gasto', 'custo']):
        exp = get_monthly_expenses(user.id)
        return f"💸 **Despesas do mês:** {_fmt_brl(exp)}\n\nAcesse o **Financeiro** para ver o detalhamento por categoria."

    # 4. Faturas pendentes
    if 'invoices' in intents:
        p = get_pending_invoices(user.id)
        if p['count'] == 0:
            return "✅ **Nenhuma fatura pendente** no momento. Tudo em dia!"
        return f"📋 Você tem **{p['count']} fatura{'s' if p['count']!=1 else ''} pendente{'s' if p['count']!=1 else ''}**, totalizando **{_fmt_brl(p['total'])}**.\n\nVeja em **Financeiro → Faturas**."

    # 5. Leads / CRM
    if 'crm' in intents:
        pipe = get_pipeline_summary(user.id)
        conv = get_conversion_rate(user.id)
        new30 = get_new_leads(user.id, 30)
        contacts = get_contacts_count(user.id)
        if pipe['total_leads'] == 0:
            return ("Ainda **não há leads** cadastrados. Crie seu primeiro lead em **CRM → Pipeline** para que eu possa analisar suas oportunidades.")

        active = pipe['by_stage']
        out = (
            f"🎯 **Visão geral de CRM:**\n\n"
            f"- **Contatos ativos:** {contacts}\n"
            f"- **Novos leads (30 dias):** {new30}\n"
            f"- **Valor ativo no pipeline:** {_fmt_brl(pipe['active_value'])}\n"
            f"- **Taxa de conversão:** **{conv['rate_pct']}%** ({conv['won']} ganhos, {conv['lost']} perdidos)\n\n"
            f"**Distribuição por estágio:**\n"
        )
        labels = {'prospect': 'Prospect', 'qualified': 'Qualificado', 'proposal': 'Proposta',
                  'negotiation': 'Negociação', 'closed_won': 'Ganho', 'closed_lost': 'Perdido'}
        for stage, info in active.items():
            if info['count']:
                out += f"- {labels[stage]}: {info['count']} lead(s) — {_fmt_brl(info['total_value'])}\n"
        return out

    # 6. Crescimento
    if 'growth' in intents or 'summary' in intents:
        g = get_growth_metrics(user.id)
        m = get_profit_margin(user.id)
        pipe = get_pipeline_summary(user.id)
        return (
            f"📈 **Resumo executivo:**\n\n"
            f"- **Receita 30d:** {_fmt_brl(g['revenue_30d'])} ({g['revenue_growth_pct']:+.1f}% vs 30d anteriores)\n"
            f"- **Novos contatos 30d:** {g['contacts_30d']} ({g['contacts_growth_pct']:+.1f}%)\n"
            f"- **Margem do mês:** {m['margin_pct']}%\n"
            f"- **Pipeline ativo:** {_fmt_brl(pipe['active_value'])} em {pipe['total_leads']} leads\n\n"
            f"💡 **Sugestões para crescer:**\n"
            f"- Acelere leads em estágio de Proposta/Negociação\n"
            f"- Configure automações de follow-up\n"
            f"- Revise as top categorias de receita e dobre a aposta na mais rentável"
        )

    # 7. Automações
    if 'automation' in intents:
        a = get_automation_stats(user.id)
        return (
            f"⚡ **Automações:**\n\n"
            f"- Total: {a['total']}\n"
            f"- Ativas: {a['active']}\n"
            f"- Execuções totais: {a['total_runs']}\n\n"
            f"Configure mais fluxos em **Automação** — sugiro um follow-up automático para leads novos."
        )

    # 8. Default — resposta amigável + lembrete de API key
    return (
        f"Olá, {user.first_name}! Sou o **VEXX AI**, seu assistente empresarial.\n\n"
        f"Posso analisar suas finanças, leads, faturas e crescimento usando seus dados reais.\n\n"
        f"Tente perguntar:\n"
        f"- *\"Qual minha margem de lucro este mês?\"*\n"
        f"- *\"Quantos leads novos tive nos últimos 30 dias?\"*\n"
        f"- *\"Como está meu pipeline?\"*\n"
        f"- *\"Faça um resumo executivo do negócio\"*\n\n"
        f"💡 Para conversas abertas com IA avançada (OpenAI, Claude, DeepSeek), "
        f"configure uma **API Key** em **Configurações → API Keys**."
    )


# ──────────────────────────────────────────────────────────────────────────────
# Conversation management
# ──────────────────────────────────────────────────────────────────────────────

def list_conversations(user_id: int) -> list:
    convs = AIConversation.query.filter_by(user_id=user_id).order_by(
        AIConversation.updated_at.desc()
    ).limit(40).all()
    return [{
        'id': c.id, 'title': c.title,
        'updated_at': c.updated_at.isoformat() if c.updated_at else '',
    } for c in convs]


def get_conversation(user_id: int, conv_id: int) -> dict | None:
    conv = AIConversation.query.filter_by(id=conv_id, user_id=user_id).first()
    if not conv:
        return None
    messages = json.loads(conv.messages or '[]')
    return {
        'id': conv.id, 'title': conv.title,
        'messages': [{'role': m['role'], 'content': m['content']} for m in messages],
        'updated_at': conv.updated_at.isoformat() if conv.updated_at else '',
    }


def rename_conversation(user_id: int, conv_id: int, new_title: str) -> tuple[bool, str]:
    conv = AIConversation.query.filter_by(id=conv_id, user_id=user_id).first()
    if not conv:
        return False, 'Conversa não encontrada.'
    title = (new_title or '').strip()[:120]
    if not title:
        return False, 'Título não pode ser vazio.'
    conv.title = title
    db.session.commit()
    return True, 'Conversa renomeada.'


def delete_conversation(user_id: int, conv_id: int) -> tuple[bool, str]:
    conv = AIConversation.query.filter_by(id=conv_id, user_id=user_id).first()
    if not conv:
        return False, 'Conversa não encontrada.'
    db.session.delete(conv)
    db.session.commit()
    return True, 'Conversa removida.'
