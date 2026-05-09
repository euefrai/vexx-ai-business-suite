/* ══════════════════════════════════════════════════════════
   VEXX AI — Analytics page
══════════════════════════════════════════════════════════ */

let _trendChart = null, _leadsChart = null;

const STAGE_LABEL = {
  prospect: 'Prospect', qualified: 'Qualif.', proposal: 'Proposta',
  negotiation: 'Negoc.', closed_won: 'Ganho', closed_lost: 'Perdido',
};

document.addEventListener('DOMContentLoaded', () => {
  loadOverview();
  loadTrend(30);
  loadLeadsByStage();
  loadCategories();
});

async function loadOverview() {
  try {
    const res = await vexxAPI.get('/api/analytics/overview');
    const d = res.data;

    document.getElementById('ana-contacts').textContent = formatNumber(d.contacts_30d);
    setTrend('ana-contacts-trend', d.contacts_growth);
    document.getElementById('ana-revenue').textContent  = formatBRL(d.revenue_30d);
    setTrend('ana-revenue-trend', d.revenue_growth);
    document.getElementById('ana-conversion').textContent = `${d.conversion_rate}%`;
    document.getElementById('ana-leads-total').textContent = formatNumber(d.total_leads);
    document.getElementById('ana-won').textContent = `${d.leads_won} ganhos`;
    document.getElementById('conv-won').textContent  = formatNumber(d.leads_won);
    document.getElementById('conv-lost').textContent = formatNumber(d.leads_lost);
  } catch {}
}

function setTrend(id, pct) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = `${pct >= 0 ? '+' : ''}${pct}%`;
  el.className = `kpi-trend ${pct >= 0 ? 'kpi-trend-up' : 'kpi-trend-down'}`;
}

function switchTrend(btn, days) {
  document.querySelectorAll('.period-tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  loadTrend(days);
}

async function loadTrend(days = 30) {
  try {
    const res = await vexxAPI.get(`/api/analytics/revenue-trend?days=${days}`);
    const data = res.data || [];
    const ctx = document.getElementById('trend-chart');

    if (_trendChart) _trendChart.destroy();
    _trendChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: data.map(d => d.date),
        datasets: [
          { label: 'Receita', data: data.map(d => d.income), borderColor: 'rgba(16,185,129,0.9)', backgroundColor: 'rgba(16,185,129,0.1)', borderWidth: 2, tension: 0.35, fill: true, pointRadius: 0 },
          { label: 'Despesa', data: data.map(d => d.expenses), borderColor: 'rgba(244,63,94,0.9)', backgroundColor: 'rgba(244,63,94,0.08)', borderWidth: 2, tension: 0.35, fill: true, pointRadius: 0 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => ` ${c.dataset.label}: ${formatBRL(c.raw)}` } } },
        scales: {
          x: { grid: { display: false }, ticks: { maxTicksLimit: 8, font: { size: 10 } } },
          y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { callback: v => v >= 1000 ? `R$${(v/1000).toFixed(0)}K` : `R$${v}`, font: { size: 10 } } },
        },
      },
    });
  } catch {}
}

async function loadLeadsByStage() {
  try {
    const res = await vexxAPI.get('/api/analytics/leads-by-stage');
    const data = res.data || [];
    const ctx = document.getElementById('leads-chart');

    if (_leadsChart) _leadsChart.destroy();
    _leadsChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.map(d => STAGE_LABEL[d.stage] || d.stage),
        datasets: [{
          label: 'Leads',
          data: data.map(d => d.count),
          backgroundColor: ['rgba(59,130,246,0.7)','rgba(99,102,241,0.7)','rgba(139,92,246,0.7)','rgba(168,85,247,0.7)','rgba(16,185,129,0.7)','rgba(244,63,94,0.7)'],
          borderRadius: 6, borderSkipped: false,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => ` ${c.raw} leads` } } },
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 10 } } },
          y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { stepSize: 1, font: { size: 10 } } },
        },
      },
    });
  } catch {}
}

async function loadCategories() {
  const wrap = document.getElementById('categories-list');
  try {
    const res = await vexxAPI.get('/api/analytics/top-categories');
    const items = res.data || [];

    if (!items.length) {
      wrap.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-faint);font-size:.85rem">Sem categorias ainda. Adicione transações com categoria.</div>';
      return;
    }

    const max = Math.max(...items.map(i => i.total), 1);
    wrap.innerHTML = items.map(i => `
      <div style="margin-bottom:12px">
        <div style="display:flex;justify-content:space-between;font-size:.82rem;margin-bottom:5px">
          <span>${esc(i.category)}</span>
          <strong style="color:var(--green)">${formatBRL(i.total)}</strong>
        </div>
        <div class="kpi-progress" style="height:5px"><div class="kpi-progress-bar" style="width:${(i.total/max)*100}%;background:linear-gradient(90deg,var(--green),var(--teal))"></div></div>
      </div>`).join('');
  } catch {
    wrap.innerHTML = '<div style="color:var(--red);padding:16px">Erro ao carregar.</div>';
  }
}

function esc(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
