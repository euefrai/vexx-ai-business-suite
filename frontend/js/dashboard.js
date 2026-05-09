/* ══════════════════════════════════════════════════════════
   VEXX AI — Dashboard Data & Interactions
══════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', async () => {
  await loadUser();
  await Promise.all([
    loadKPIs(),
    loadTransactions(),
    loadPipeline(),
    loadActivity(),
    loadChartData('6m'),
  ]);
  loadAIInsight();
});

/* ── User Info ──────────────────────────────────────────── */
async function loadUser() {
  try {
    const res  = await vexxAPI.get('/api/auth/me');
    const user = res.data;

    const firstName = user.first_name || 'Usuário';
    const fullName  = [user.first_name, user.last_name].filter(Boolean).join(' ');
    const initials  = ((user.first_name?.[0] || '') + (user.last_name?.[0] || '')).toUpperCase() || 'U';
    const planLabels = { free: 'Free', pro: 'Pro ✦', enterprise: 'Enterprise' };
    const plan       = planLabels[user.plan] || 'Free';

    /* Greeting by time of day */
    const h = new Date().getHours();
    setText('welcome-heading', `${h < 12 ? 'Bom dia' : h < 18 ? 'Boa tarde' : 'Boa noite'} 👋`);
    setText('welcome-name', firstName);

    /* Sidebar */
    setText('s-user-name', fullName);
    setText('s-user-company', user.company || 'Sem empresa');
    setInitials('s-user-avi', initials);

    /* Topbar */
    setText('t-user-name', firstName);
    setInitials('t-user-avi', initials);

    /* Dropdown */
    setText('d-user-name', fullName);
    setText('d-user-email', user.email || '');
    setText('d-user-plan', planLabels[user.plan] || 'Free');
    setInitials('d-user-avi', initials);

    /* Plan badge */
    setText('topbar-plan-label', user.plan === 'free' ? 'Free' : user.plan === 'pro' ? 'Pro' : 'Enterprise');

    /* AI usage count on mini KPI */
    const aiEl = document.getElementById('kpi-ai-usage');
    if (aiEl) animateCounter(aiEl, user.ai_usage_count || 0, formatNumber);

    /* Hide upgrade CTA for paid plans */
    if (user.plan !== 'free') {
      document.getElementById('sidebar-upgrade')?.classList.add('hidden');
    }

  } catch (err) {
    console.error('loadUser:', err);
  }
}

/* ── KPIs ───────────────────────────────────────────────── */
async function loadKPIs() {
  try {
    const res  = await vexxAPI.get('/api/dashboard/stats');
    const d    = res.data;

    /* Revenue */
    animateCounter(document.getElementById('kpi-rev'), d.revenue || 0, formatBRL);
    const chg = d.revenue_change || 0;
    const chgEl = document.getElementById('kpi-rev-change');
    if (chgEl) {
      chgEl.textContent = `${chg >= 0 ? '+' : ''}${chg}%`;
      chgEl.className   = `kpi-trend ${chg >= 0 ? 'kpi-trend-up' : 'kpi-trend-down'}`;
    }
    drawSparkline('spark-rev', generateSparkline(d.revenue || 0));

    /* Contacts */
    const contacts = d.total_contacts || 0;
    animateCounter(document.getElementById('kpi-contacts'), contacts, formatNumber);
    const contactPct = Math.min(contacts / 100 * 100, 100);
    setStyle('kpi-contacts-bar', 'width', `${contactPct}%`);
    setText('kpi-contacts-badge', `${contacts} contatos`);

    /* Leads pipeline */
    const leadsVal   = d.leads_pipeline_value || 0;
    const leadsCount = d.active_leads || 0;
    animateCounter(document.getElementById('kpi-leads-val'), leadsVal, formatBRL);
    setText('kpi-leads-count', `${leadsCount} ativos`);
    drawSparkline('spark-leads', generateSparkline(leadsVal));

    /* Automations */
    const autos = d.active_automations || 0;
    animateCounter(document.getElementById('kpi-automations'), autos, formatNumber);
    setText('kpi-auto-label', `${autos} ativa${autos !== 1 ? 's' : ''}`);
    setStyle('kpi-auto-bar', 'width', `${Math.min(autos * 20, 100)}%`);

    /* Secondary KPIs */
    const income   = d.revenue   || 0;
    const expenses = d.expenses  || 0;
    const profit   = d.profit    || income - expenses;
    const profitPct = income > 0 ? Math.round((profit / income) * 100) : 0;

    animateCounter(document.getElementById('kpi-profit'),   profit,   formatBRL);
    animateCounter(document.getElementById('kpi-expenses'), expenses, formatBRL);
    setText('kpi-profit-pct', `${profitPct >= 0 ? '+' : ''}${profitPct}%`);

    /* Conversion rate: leads / contacts */
    const conv = contacts > 0 ? Math.round((leadsCount / contacts) * 100) : 0;
    setText('kpi-conversion', `${conv}%`);

    /* Overview stats */
    setText('ov-income',  formatBRL(income));
    setText('ov-expense', formatBRL(expenses));
    setText('ov-leads',   formatNumber(leadsCount));
    setText('ov-autos',   formatNumber(autos));

    /* Sidebar nav badge */
    setText('nav-crm-count',  contacts);
    setText('nav-auto-badge', autos);

    /* Pending invoices — optional secondary call */
    loadPendingInvoices();

  } catch (err) {
    console.error('loadKPIs:', err);
  }
}

async function loadPendingInvoices() {
  try {
    const res = await vexxAPI.get('/api/finance/invoices?status=pending');
    const count = (res.data || []).length;
    animateCounter(document.getElementById('kpi-invoices'), count, formatNumber);
  } catch { /* non-critical */ }
}

/* ── Transactions ───────────────────────────────────────── */
async function loadTransactions() {
  const list = document.getElementById('tx-list');
  if (!list) return;

  try {
    const res   = await vexxAPI.get('/api/finance/transactions?limit=5');
    const items = res.data || [];

    setText('tx-subtitle', `${items.length} recentes`);

    if (!items.length) {
      list.innerHTML = emptyState('Nenhuma transação ainda');
      return;
    }

    list.innerHTML = items.map(tx => {
      const isIncome = tx.type === 'income';
      return `
        <div class="tx-item ${isIncome ? 'tx-income' : 'tx-expense'}">
          <div class="tx-icon">
            <i data-lucide="${isIncome ? 'arrow-up-right' : 'arrow-down-right'}" size="14"></i>
          </div>
          <div class="tx-info">
            <div class="tx-desc">${esc(tx.description)}</div>
            <div class="tx-date">${formatDate(tx.date)}${tx.category ? ' · ' + esc(tx.category) : ''}</div>
          </div>
          <div class="tx-amount">${isIncome ? '+' : '-'}${formatBRL(Math.abs(tx.amount))}</div>
        </div>`;
    }).join('');

    if (window.lucide) lucide.createIcons();

  } catch {
    list.innerHTML = errorState('Erro ao carregar transações');
  }
}

/* ── Pipeline Mini ──────────────────────────────────────── */
async function loadPipeline() {
  const container = document.getElementById('pipeline-mini');
  if (!container) return;

  try {
    const res    = await vexxAPI.get('/api/crm/pipeline');
    const stages = (res.data || []).filter(s => s.count > 0);

    if (!stages.length) {
      container.innerHTML = emptyState('Nenhum lead no pipeline');
      return;
    }

    const maxCount = Math.max(...stages.map(s => s.count), 1);
    const labels = {
      prospect: 'Prospecção', qualified: 'Qualif.', proposal: 'Proposta',
      negotiation: 'Negociação', closed_won: 'Ganho', closed_lost: 'Perdido',
    };

    container.innerHTML = stages.slice(0, 6).map(s => `
      <div class="pipeline-stage-row">
        <div class="pipeline-stage-name" title="${esc(s.stage)}">
          ${labels[s.stage] || esc(s.stage)}
        </div>
        <div class="pipeline-stage-bar-wrap">
          <div class="pipeline-stage-bar" style="width:${(s.count / maxCount) * 100}%"></div>
        </div>
        <div class="pipeline-stage-count">${s.count}</div>
      </div>`
    ).join('');

  } catch {
    container.innerHTML = errorState('Erro ao carregar pipeline');
  }
}

/* ── Activity Feed ──────────────────────────────────────── */
async function loadActivity() {
  const feed = document.getElementById('activity-feed');
  if (!feed) return;

  try {
    const res      = await vexxAPI.get('/api/dashboard/activity');
    const activity = res.data || [];

    if (!activity.length) {
      feed.innerHTML = emptyState('Nenhuma atividade recente');
      return;
    }

    const styleMap = {
      contact:     { bg: 'var(--blue-soft)',    color: 'var(--blue)',         icon: 'user-plus'    },
      lead:        { bg: 'var(--amber-soft)',   color: 'var(--amber)',        icon: 'target'       },
      transaction: { bg: 'var(--green-soft)',   color: 'var(--green)',        icon: 'dollar-sign'  },
      automation:  { bg: 'var(--purple-soft)',  color: 'var(--purple)',       icon: 'zap'          },
      ai:          { bg: 'var(--accent-soft)',  color: 'var(--accent-light)', icon: 'bot'          },
    };

    feed.innerHTML = activity.map(item => {
      const s = styleMap[item.type] || styleMap.contact;
      return `
        <div class="activity-item">
          <div class="activity-icon" style="background:${s.bg};color:${s.color}">
            <i data-lucide="${s.icon}" size="13"></i>
          </div>
          <div class="activity-body">
            <div class="activity-text">${esc(item.text)}</div>
            <div class="activity-time">${item.time || ''}</div>
          </div>
        </div>`;
    }).join('');

    if (window.lucide) lucide.createIcons();

  } catch {
    feed.innerHTML = errorState('Erro ao carregar atividade');
  }
}

/* ── Chart Data ─────────────────────────────────────────── */
async function loadChartData(period = '6m') {
  try {
    const res    = await vexxAPI.get('/api/dashboard/chart');
    const months = res.data || [];

    const chartData = {
      labels:   months.map(m => m.label),
      revenue:  months.map(m => m.revenue),
      expenses: months.map(m => m.expenses),
    };
    initRevenueChart(chartData);

  } catch {
    initRevenueChart(null);
  }
}

/* ── AI Insight ─────────────────────────────────────────── */
async function loadAIInsight() {
  const box      = document.getElementById('ai-insight-box');
  const statusEl = document.getElementById('ai-status');
  if (!box) return;

  try {
    const res = await vexxAPI.post('/api/ai/chat', {
      message: 'Dê-me um resumo executivo rápido do estado atual do negócio em 1-2 frases, de forma motivadora e objetiva.',
    });

    if (statusEl) statusEl.textContent = 'Pronto para ajudar';
    const reply = res.data?.reply || 'IA pronta para análise.';
    box.innerHTML = `<p style="font-size:0.845rem;line-height:1.65;color:var(--text-muted);margin:0">${esc(reply)}</p>`;

  } catch {
    if (statusEl) statusEl.textContent = 'Configure uma API key';
    box.innerHTML = `<p style="font-size:0.845rem;color:var(--text-faint);margin:0">
      Configure uma chave de API em <a href="/settings" style="color:var(--accent-light)">Configurações</a> para ativar análise por IA.
    </p>`;
  }
}

/* ── AI Quick Actions ───────────────────────────────────── */
function askAI(prompt) {
  window.location.href = `/ai-assistant?q=${encodeURIComponent(prompt)}`;
}

function sendInlineAI() {
  const input = document.getElementById('ai-inline-input');
  const query = input?.value?.trim();
  if (!query) return;
  input.value = '';
  window.location.href = `/ai-assistant?q=${encodeURIComponent(query)}`;
}

/* ── Helpers ────────────────────────────────────────────── */
function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = (val === null || val === undefined) ? '—' : val;
}

function setStyle(id, prop, val) {
  const el = document.getElementById(id);
  if (el) el.style[prop] = val;
}

function setInitials(id, initials) {
  const el = document.getElementById(id);
  if (el) el.textContent = (initials || 'U').slice(0, 2);
}

function esc(str) {
  return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function emptyState(msg) {
  return `<div style="padding:20px;text-align:center;color:var(--text-faint);font-size:0.84rem">${msg}</div>`;
}

function errorState(msg) {
  return `<div style="padding:16px;color:var(--text-faint);font-size:0.84rem">${msg}</div>`;
}

/* Generate a plausible sparkline from a single value (ascending trend) */
function generateSparkline(current) {
  if (!current) return [0, 0, 0, 0, 0, 0, 0];
  const base = current * 0.6;
  return [
    base * 0.5, base * 0.7, base * 0.8, base * 0.9, base, current * 0.95, current,
  ];
}
