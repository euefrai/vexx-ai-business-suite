/* ══════════════════════════════════════════════════════════
   VEXX AI — Finance page
══════════════════════════════════════════════════════════ */

let _txFilter = '';
let _financeChart = null;

document.addEventListener('DOMContentLoaded', () => {
  loadSummary();
  loadTransactions();
  loadInvoices();
  loadFinanceChart();
  loadContactsForInvoice();
  document.getElementById('tx-date').value = new Date().toISOString().slice(0, 10);
});

/* ── Summary KPIs ── */
async function loadSummary() {
  try {
    const res = await vexxAPI.get('/api/finance/summary');
    const d = res.data;
    document.getElementById('fin-income').textContent   = formatBRL(d.month_income);
    document.getElementById('fin-expenses').textContent = formatBRL(d.month_expenses);
    document.getElementById('fin-profit').textContent   = formatBRL(d.month_profit);
    document.getElementById('fin-pending').textContent  = formatBRL(d.pending_amount);
    document.getElementById('fin-pending-count').textContent = `${d.pending_invoices} fatura${d.pending_invoices !== 1 ? 's' : ''} pendente${d.pending_invoices !== 1 ? 's' : ''}`;
    document.getElementById('ov-total-income').textContent  = formatBRL(d.total_income);
    document.getElementById('ov-total-expense').textContent = formatBRL(d.total_expenses);
    document.getElementById('ov-balance').textContent       = formatBRL(d.balance);
  } catch {}
}

/* ── Chart ── */
async function loadFinanceChart() {
  try {
    const res = await vexxAPI.get('/api/dashboard/chart');
    const months = res.data || [];
    const ctx = document.getElementById('finance-chart');
    if (!ctx) return;

    if (_financeChart) _financeChart.destroy();
    _financeChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: months.map(m => m.label),
        datasets: [
          { label: 'Receita',  data: months.map(m => m.revenue),  backgroundColor: 'rgba(16,185,129,0.75)', borderRadius: 6, borderSkipped: false },
          { label: 'Despesas', data: months.map(m => m.expenses), backgroundColor: 'rgba(244,63,94,0.65)',  borderRadius: 6, borderSkipped: false },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => ` ${c.dataset.label}: ${formatBRL(c.raw)}` } } },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.04)' } },
          y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { callback: v => v >= 1000 ? `R$${(v/1000).toFixed(0)}K` : `R$${v}` } },
        },
      },
    });
  } catch {}
}

/* ── Transactions ── */
function filterTx(btn, type) {
  document.querySelectorAll('.period-tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  _txFilter = type;
  loadTransactions();
}

async function loadTransactions() {
  const list = document.getElementById('tx-list');
  try {
    const url = _txFilter ? `/api/finance/transactions?type=${_txFilter}&limit=50` : '/api/finance/transactions?limit=50';
    const res = await vexxAPI.get(url);
    const items = res.data || [];

    document.getElementById('tx-count').textContent = `${items.length} transaç${items.length !== 1 ? 'ões' : 'ão'}`;

    if (!items.length) {
      list.innerHTML = '<div style="padding:24px;text-align:center;color:var(--text-faint);font-size:.85rem">Nenhuma transação registrada.</div>';
      return;
    }

    list.innerHTML = items.map(tx => {
      const isInc = tx.type === 'income';
      return `
        <div class="tx-item ${isInc ? 'tx-income' : 'tx-expense'}">
          <div class="tx-icon"><i data-lucide="${isInc ? 'arrow-up-right' : 'arrow-down-right'}" size="14"></i></div>
          <div class="tx-info">
            <div class="tx-desc">${esc(tx.description)}</div>
            <div class="tx-date">${formatDate(tx.date)}${tx.category ? ' · ' + esc(tx.category) : ''}</div>
          </div>
          <div style="display:flex;align-items:center;gap:8px">
            <div class="tx-amount">${isInc ? '+' : '-'}${formatBRL(Math.abs(tx.amount))}</div>
            <button class="btn-ghost btn-icon btn-sm" onclick="deleteTx(${tx.id})" style="color:var(--red)" title="Remover"><i data-lucide="trash-2" size="12"></i></button>
          </div>
        </div>`;
    }).join('');
    if (window.lucide) lucide.createIcons();
  } catch {
    list.innerHTML = '<div style="color:var(--red);padding:16px">Erro ao carregar transações.</div>';
  }
}

function openTxModal() {
  document.getElementById('tx-amount').value = '';
  document.getElementById('tx-desc').value   = '';
  document.getElementById('tx-category').value = '';
  document.getElementById('tx-date').value   = new Date().toISOString().slice(0, 10);
  document.getElementById('tx-type').value   = 'income';
  openModal('tx-modal');
}

async function saveTx(e) {
  e.preventDefault();
  try {
    await vexxAPI.post('/api/finance/transactions', {
      type:        document.getElementById('tx-type').value,
      amount:      parseFloat(document.getElementById('tx-amount').value),
      description: document.getElementById('tx-desc').value.trim(),
      category:    document.getElementById('tx-category').value.trim(),
      date:        document.getElementById('tx-date').value || null,
    });
    showToast('Transação registrada', 'success');
    closeModal('tx-modal');
    loadSummary(); loadTransactions(); loadFinanceChart();
  } catch (err) {
    showToast(err.message || 'Erro ao salvar', 'error');
  }
}

async function deleteTx(id) {
  if (!confirm('Remover esta transação?')) return;
  try {
    await vexxAPI.delete(`/api/finance/transactions/${id}`);
    showToast('Removida', 'success');
    loadSummary(); loadTransactions(); loadFinanceChart();
  } catch (err) { showToast(err.message || 'Erro', 'error'); }
}

/* ── Invoices ── */
async function loadInvoices() {
  const list = document.getElementById('invoices-list');
  try {
    const res = await vexxAPI.get('/api/finance/invoices');
    const items = res.data || [];

    if (!items.length) {
      list.innerHTML = '<div style="padding:24px;text-align:center;color:var(--text-faint);font-size:.85rem">Nenhuma fatura ainda.</div>';
      return;
    }

    const statusBadge = {
      pending: '<span class="badge badge-amber">Pendente</span>',
      paid:    '<span class="badge badge-green">Paga</span>',
      overdue: '<span class="badge badge-red">Vencida</span>',
    };

    list.innerHTML = items.map(inv => `
      <div class="tx-item" style="flex-direction:column;align-items:stretch;gap:8px">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <div>
            <div class="tx-desc">${esc(inv.invoice_number)}</div>
            <div class="tx-date">Vence ${inv.due_date ? formatDate(inv.due_date) : '—'}</div>
          </div>
          <div class="tx-amount" style="color:var(--text)">${formatBRL(inv.amount)}</div>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center">
          ${statusBadge[inv.status] || ''}
          <div style="display:flex;gap:4px">
            ${inv.status !== 'paid' ? `<button class="btn-ghost btn-sm" onclick="markPaid(${inv.id})" style="color:var(--green)" title="Marcar paga"><i data-lucide="check" size="11"></i> Pagar</button>` : ''}
          </div>
        </div>
      </div>`).join('');
    if (window.lucide) lucide.createIcons();
  } catch {
    list.innerHTML = '<div style="color:var(--red);padding:16px">Erro ao carregar faturas.</div>';
  }
}

async function loadContactsForInvoice() {
  try {
    const res = await vexxAPI.get('/api/crm/contacts');
    const sel = document.getElementById('inv-contact');
    sel.innerHTML = '<option value="">— Nenhum —</option>' +
      (res.data || []).map(c => `<option value="${c.id}">${esc(c.name)}${c.company ? ' (' + esc(c.company) + ')' : ''}</option>`).join('');
  } catch {}
}

function openInvoiceModal() {
  ['inv-amount','inv-due','inv-desc'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('inv-status').value  = 'pending';
  document.getElementById('inv-contact').value = '';
  openModal('invoice-modal');
}

async function saveInvoice(e) {
  e.preventDefault();
  const contactId = document.getElementById('inv-contact').value;
  try {
    await vexxAPI.post('/api/finance/invoices', {
      amount:      parseFloat(document.getElementById('inv-amount').value),
      due_date:    document.getElementById('inv-due').value || null,
      contact_id:  contactId ? parseInt(contactId, 10) : null,
      description: document.getElementById('inv-desc').value.trim(),
      status:      document.getElementById('inv-status').value,
    });
    showToast('Fatura criada', 'success');
    closeModal('invoice-modal');
    loadInvoices(); loadSummary();
  } catch (err) {
    showToast(err.message || 'Erro', 'error');
  }
}

async function markPaid(id) {
  try {
    await vexxAPI.request('PATCH', `/api/finance/invoices/${id}/status`, { status: 'paid' });
    showToast('Fatura marcada como paga', 'success');
    loadInvoices(); loadSummary();
  } catch (err) { showToast(err.message || 'Erro', 'error'); }
}

function esc(str) {
  return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
