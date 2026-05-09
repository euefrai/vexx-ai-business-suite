/* ══════════════════════════════════════════════════════════
   VEXX AI — Billing page
══════════════════════════════════════════════════════════ */

let _currentPlan = 'free';

document.addEventListener('DOMContentLoaded', () => {
  loadCurrent();
  loadUsage();
  loadPlans();
});

async function loadCurrent() {
  try {
    const res = await vexxAPI.get('/api/billing/current');
    _currentPlan = res.data.plan;
    document.getElementById('cur-plan-name').textContent = res.data.name;
  } catch {}
}

async function loadUsage() {
  const grid = document.getElementById('usage-grid');
  try {
    const res = await vexxAPI.get('/api/billing/usage');
    const u = res.data;

    const labels = {
      contacts: { name: 'Contatos',     icon: 'users' },
      leads:    { name: 'Leads',        icon: 'target' },
      automations: { name: 'Automações', icon: 'zap' },
      ai_requests: { name: 'IA',         icon: 'bot' },
      invoices: { name: 'Faturas',      icon: 'file-text' },
    };

    grid.innerHTML = Object.keys(labels).map(key => {
      const item = u[key]; const meta = labels[key];
      const lim = item.limit;
      const unlimited = lim === -1;
      const pct = unlimited ? 5 : Math.min((item.used / lim) * 100, 100);
      const warn = pct > 80;

      return `
        <div>
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
            <i data-lucide="${meta.icon}" size="13" style="color:var(--text-muted)"></i>
            <span style="font-size:.78rem;color:var(--text-muted)">${meta.name}</span>
          </div>
          <div style="font-size:1rem;font-weight:700">${formatNumber(item.used)} <span style="color:var(--text-faint);font-size:.78rem;font-weight:400">/ ${unlimited ? '∞' : formatNumber(lim)}</span></div>
          <div class="usage-bar"><div class="usage-fill ${warn ? 'warning' : ''}" style="width:${pct}%"></div></div>
        </div>`;
    }).join('');

    if (window.lucide) lucide.createIcons();
  } catch {
    grid.innerHTML = '<p style="color:var(--red)">Erro ao carregar uso.</p>';
  }
}

async function loadPlans() {
  const grid = document.getElementById('plans-grid');
  try {
    const res = await vexxAPI.get('/api/billing/plans');
    const plans = res.data || [];

    grid.innerHTML = plans.map(p => {
      const isCurrent  = p.id === _currentPlan;
      const isFeatured = p.id === 'pro' && !isCurrent;
      const cls = `plan-card ${isFeatured ? 'featured' : ''} ${isCurrent ? 'current' : ''}`;
      const price = p.price === 0 ? 'Grátis' : `R$ ${p.price}<small>/mês</small>`;

      const btn = isCurrent
        ? `<button class="btn btn-secondary btn-full" disabled style="opacity:.6;cursor:default">Plano atual</button>`
        : `<button class="btn btn-primary btn-full" onclick='showDevMessage()'><i data-lucide="lock" size="14"></i> ${p.price === 0 ? 'Fazer downgrade' : 'Fazer upgrade'}</button>`;

      return `
        <div class="${cls}">
          <div class="plan-name">${p.name}</div>
          <div class="plan-price">${price}</div>
          <ul class="plan-features">
            ${p.features.map(f => `<li>${f}</li>`).join('')}
          </ul>
          ${btn}
        </div>`;
    }).join('');
  } catch {
    grid.innerHTML = '<p style="color:var(--red)">Erro ao carregar planos.</p>';
  }
}

async function upgradePlan(planId) {
  if (!confirm(`Confirmar mudança para o plano ${planId.toUpperCase()}?`)) return;
  try {
    const res = await vexxAPI.post('/api/billing/upgrade', { plan: planId });
    showToast(res.message || 'Plano atualizado', 'success');
    setTimeout(() => window.location.reload(), 800);
  } catch (err) {
    showToast(err.message || 'Erro ao atualizar plano', 'error');
  }
}

window.showDevMessage = function() {
  if (typeof showToast === 'function') {
    showToast('Em desenvolvimento 🚧', 'info');
  } else {
    alert('Em desenvolvimento 🚧');
  }
}
