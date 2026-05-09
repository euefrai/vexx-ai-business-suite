/* ══════════════════════════════════════════════════════════
   VEXX AI — Automation Hub (6 tabs)
══════════════════════════════════════════════════════════ */

let _providers   = [];
let _categories  = {};
let _selectedCat = 'all';
let _integrations = [];
let _automations  = [];
let _triggers    = [];
let _actions     = [];
let _contacts    = [];   /* cache para autocomplete */

document.addEventListener('DOMContentLoaded', async () => {
  /* Tab switching */
  document.querySelectorAll('.auto-tab').forEach(t => {
    t.addEventListener('click', () => goTab(t.dataset.tab));
  });

  /* Form submissions */
  document.getElementById('wf-form').addEventListener('submit', saveWorkflow);
  document.getElementById('connect-form').addEventListener('submit', saveConnection);

  /* Initial load */
  await loadCatalog();
  loadStats();
  loadAutomations();
  loadIntegrations();
  loadProviders();
  loadTemplates();
  loadSuggestions();
  loadLogs();
  setupWebhooks();
});

/* ── Tabs ───────────────────────────────────────────────── */
function goTab(name) {
  document.querySelectorAll('.auto-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
  document.querySelectorAll('.auto-section').forEach(s => s.classList.toggle('active', s.id === `section-${name}`));
  if (name === 'webhooks') setupWebhooks();
  acClose(); /* limpa autocomplete ao trocar tab */
}

/* ── KPIs ───────────────────────────────────────────────── */
async function loadStats() {
  try {
    const res = await vexxAPI.get('/api/automation/stats');
    const d = res.data;
    document.getElementById('kpi-total').textContent   = d.total;
    document.getElementById('kpi-active').textContent  = d.active;
    document.getElementById('kpi-runs').textContent    = d.total_runs;
    document.getElementById('kpi-success').textContent = `${d.success_rate}%`;
    document.getElementById('tab-count-workflows').textContent = d.total;
  } catch {}
}

/* ── Catálogo de triggers/actions ───────────────────────── */
async function loadCatalog() {
  try {
    const res = await vexxAPI.get('/api/automation/catalog');
    _triggers = res.data.triggers || [];
    _actions  = res.data.actions  || [];

    const tSel = document.getElementById('wf-trigger');
    if (tSel) tSel.innerHTML = _triggers.map(t => `<option value="${t.id}">${t.label}</option>`).join('');

    /* Webhook events list */
    const wrap = document.getElementById('webhook-events');
    if (wrap) {
      wrap.innerHTML = _triggers.map(t => `
        <div style="padding:8px 12px;background:var(--surface-md);border-radius:var(--r-sm);font-size:.78rem;display:flex;align-items:center;gap:8px">
          <i data-lucide="${t.icon}" size="13" style="color:var(--accent-light)"></i>
          <code style="background:none;padding:0;color:var(--text)">${t.id}</code>
        </div>`).join('');
      if (window.lucide) lucide.createIcons();
    }
  } catch {}
}

/* ── 1. Workflows ──────────────────────────────────────── */
async function loadAutomations() {
  const list = document.getElementById('auto-list');
  try {
    const res = await vexxAPI.get('/api/automation/list');
    _automations = res.data || [];

    if (!_automations.length) {
      list.innerHTML = `
        <div style="padding:48px;text-align:center;color:var(--text-faint)">
          <div class="empty-state-icon" style="display:inline-block;margin-bottom:16px">
            <i data-lucide="zap-off" size="40" style="color:var(--accent-light);opacity:.6"></i>
          </div>
          <p style="font-size:.95rem;margin-bottom:8px;color:var(--text-muted);font-weight:600">Nenhuma automação criada</p>
          <p style="font-size:.8rem;margin-bottom:20px;max-width:340px;margin-left:auto;margin-right:auto;line-height:1.6">Use um modelo pronto ou crie uma regra simples: quando acontecer algo, faça uma ação.</p>
          <div style="display:flex;gap:10px;justify-content:center">
            <button class="btn-glass" onclick="goTab('templates')"><i data-lucide="layers" size="13"></i> Ver modelos</button>
            <button class="btn btn-primary btn-sm" onclick="openWorkflowModal()"><i data-lucide="plus" size="13"></i> Criar automação</button>
          </div>
        </div>`;
      if (window.lucide) lucide.createIcons();
      return;
    }

    list.innerHTML = _automations.map(a => {
      const tLabel = (_triggers.find(x => x.id === a.trigger) || {}).label || a.trigger;
      const aLabel = (_actions.find(x => x.id === a.action)   || {}).label || a.action;
      const tIcon  = (_triggers.find(x => x.id === a.trigger) || {}).icon  || 'zap';
      const aIcon  = (_actions.find(x => x.id === a.action)   || {}).icon  || 'play';
      return `
        <div class="workflow-card">
          <div style="width:44px;height:44px;background:linear-gradient(135deg,rgba(109,40,217,.15),rgba(67,56,202,.1));border-radius:var(--r-sm);display:grid;place-items:center;color:var(--accent-light);border:1px solid rgba(109,40,217,.15)">
            <i data-lucide="${tIcon}" size="18"></i>
          </div>
          <div style="min-width:0">
            <div style="font-weight:600;font-size:.92rem;margin-bottom:2px">${esc(a.name)}</div>
            <div style="font-size:.78rem;color:var(--text-muted);margin-bottom:4px">${esc(a.description || '—')}</div>
            <div class="wf-flow">
              <span class="step"><i data-lucide="${tIcon}" size="11"></i> ${esc(tLabel)}</span>
              <span class="arrow"><i data-lucide="arrow-right" size="11"></i></span>
              <span class="step"><i data-lucide="${aIcon}" size="11"></i> ${esc(aLabel)}</span>
              <span style="margin-left:8px;color:var(--text-faint)">· ${a.runs_count || 0} execuções</span>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px">
            <label class="switch">
              <input type="checkbox" ${a.enabled ? 'checked' : ''} onchange="toggleWf(${a.id})">
              <span class="switch-slider"></span>
            </label>
            <button class="btn-ghost btn-icon btn-sm" onclick="runWf(${a.id})" title="Executar agora"><i data-lucide="play" size="13"></i></button>
            <button class="btn-ghost btn-icon btn-sm" onclick="editWf(${a.id})" title="Editar"><i data-lucide="edit-2" size="13"></i></button>
            <button class="btn-ghost btn-icon btn-sm" onclick="deleteWf(${a.id})" title="Remover" style="color:var(--red)"><i data-lucide="trash-2" size="13"></i></button>
          </div>
        </div>`;
    }).join('');
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error(err);
    list.innerHTML = '<div style="color:var(--red);padding:16px">Erro ao carregar.</div>';
  }
}

/* ── Multi-step builder ──────────────────────────────── */
let _currentSteps = [];

function openWorkflowModal() {
  document.getElementById('wf-modal-title').textContent = 'Criar automação';
  document.getElementById('wf-id').value     = '';
  document.getElementById('wf-name').value   = '';
  document.getElementById('wf-desc').value   = '';
  document.getElementById('wf-trigger').selectedIndex = 0;
  _currentSteps = [{ action: _actions[0]?.id || 'send_email', params: {} }];
  renderSteps();
  openModal('wf-modal');
}

function editWf(id) {
  const a = _automations.find(x => x.id === id);
  if (!a) return;
  document.getElementById('wf-modal-title').textContent = 'Editar automação';
  document.getElementById('wf-id').value      = a.id;
  document.getElementById('wf-name').value    = a.name;
  document.getElementById('wf-desc').value    = a.description || '';
  document.getElementById('wf-trigger').value = a.trigger;

  let cfg = {};
  try { cfg = JSON.parse(a.config || '{}'); } catch {}
  _currentSteps = (cfg.steps && cfg.steps.length)
    ? cfg.steps
    : [{ action: a.action, params: cfg.params || {} }];
  renderSteps();
  openModal('wf-modal');
}

function addStep() {
  _currentSteps.push({ action: _actions[0]?.id || 'send_email', params: {} });
  renderSteps();
}

function removeStep(idx) {
  if (_currentSteps.length <= 1) return showToast('Pelo menos um passo é obrigatório.', 'error');
  _currentSteps.splice(idx, 1);
  renderSteps();
}

function moveStep(idx, dir) {
  const newIdx = idx + dir;
  if (newIdx < 0 || newIdx >= _currentSteps.length) return;
  [_currentSteps[idx], _currentSteps[newIdx]] = [_currentSteps[newIdx], _currentSteps[idx]];
  renderSteps();
}

function updateStepAction(idx, action) {
  _currentSteps[idx].action = action;
  _currentSteps[idx].params = {}; /* reset params ao trocar ação */
  renderSteps();
}

function updateStepParam(idx, key, value) {
  _currentSteps[idx].params[key] = value;
}

function renderSteps() {
  const wrap = document.getElementById('wf-steps');
  /* dispara em paralelo o load de contatos para ter sugestões prontas */
  ensureContactsLoaded?.();

  wrap.innerHTML = _currentSteps.map((step, idx) => {
    const actionMeta = _actions.find(a => a.id === step.action) || {};
    const fields = paramFieldsFor(step.action);

    return `
      <div style="background:var(--surface-md);border:1px solid var(--border);border-radius:var(--r);padding:14px">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
          <span style="width:24px;height:24px;background:var(--accent-soft);color:var(--accent-light);border-radius:50%;display:grid;place-items:center;font-size:.75rem;font-weight:700">${idx + 1}</span>
          <select class="form-select" style="flex:1" onchange="updateStepAction(${idx}, this.value)">
            ${_actions.map(a => `<option value="${a.id}" ${a.id === step.action ? 'selected' : ''}>${a.label}</option>`).join('')}
          </select>
          <button type="button" class="btn-ghost btn-icon btn-sm" onclick="moveStep(${idx},-1)" ${idx === 0 ? 'disabled style="opacity:.3"' : ''}><i data-lucide="arrow-up" size="13"></i></button>
          <button type="button" class="btn-ghost btn-icon btn-sm" onclick="moveStep(${idx},1)"  ${idx === _currentSteps.length - 1 ? 'disabled style="opacity:.3"' : ''}><i data-lucide="arrow-down" size="13"></i></button>
          <button type="button" class="btn-ghost btn-icon btn-sm" onclick="removeStep(${idx})" style="color:var(--red)"><i data-lucide="x" size="13"></i></button>
        </div>
        ${fields.length ? `
          <div style="display:grid;grid-template-columns:${fields.length > 1 ? '1fr 1fr' : '1fr'};gap:10px">
            ${fields.map(f => fieldHTML(idx, step.params, f)).join('')}
          </div>` : '<div style="font-size:.75rem;color:var(--text-faint)">Esta ação não precisa de configuração extra.</div>'}
      </div>`;
  }).join('');
  if (window.lucide) lucide.createIcons();
  if (typeof bindAutocomplete === 'function') bindAutocomplete();
}

function fieldHTML(stepIdx, currentParams, field) {
  const val = currentParams[field.key] || '';
  const help = field.help ? `<small style="color:var(--text-faint);font-size:.7rem;display:block;margin-top:3px">${field.help}</small>` : '';
  const autocomplete = field.autocomplete ? `data-autocomplete="${field.autocomplete}"` : '';

  if (field.type === 'textarea') {
    return `<div class="form-group" style="grid-column:1/-1;margin:0">
      <label class="form-label" style="font-size:.75rem">${field.label}</label>
      <textarea class="form-textarea" rows="3" placeholder="${escAttr(field.placeholder || '')}"
                onchange="updateStepParam(${stepIdx}, '${field.key}', this.value)"
                ${autocomplete}>${escAttr(val)}</textarea>
      ${help}
    </div>`;
  }
  return `<div class="form-group" style="margin:0;position:relative">
    <label class="form-label" style="font-size:.75rem">${field.label}</label>
    <input type="${field.type || 'text'}" class="form-input" placeholder="${escAttr(field.placeholder || '')}"
           value="${escAttr(val)}"
           onchange="updateStepParam(${stepIdx}, '${field.key}', this.value)"
           ${autocomplete} autocomplete="off" spellcheck="false">
    ${help}
  </div>`;
}

/* Mapa de campos por action */
function paramFieldsFor(actionId) {
  const map = {
    send_email: [
      { key: 'to',      label: 'Para (email)', autocomplete: 'contact-email',
        placeholder: 'email@exemplo.com ou busque por nome',
        help: 'Digite o email direto ou busque contatos pelo nome. Múltiplos separados por vírgula.' },
      { key: 'cc',      label: 'CC (opcional)', autocomplete: 'contact-email',
        placeholder: 'email ou busque contatos',
        help: 'Cópia visível — todos veem que estão na lista.' },
      { key: 'bcc',     label: 'BCC (opcional)', autocomplete: 'contact-email',
        placeholder: 'email ou busque contatos',
        help: 'Cópia oculta — destinatários não enxergam uns aos outros.' },
      { key: 'subject', label: 'Assunto', placeholder: 'Assunto do email',
        help: 'Texto direto.' },
      { key: 'body',    label: 'Corpo do email', type: 'textarea',
        placeholder: 'Olá,\n\nObrigado por entrar em contato.\n\nAtt,\nEquipe',
        help: 'Suporta HTML (detectado automaticamente).' },
    ],
    send_whatsapp: [
      { key: 'to',   label: 'Telefone',  autocomplete: 'contact-phone',
        placeholder: '+5511999999999 ou busque por nome' },
      { key: 'text', label: 'Mensagem', type: 'textarea', placeholder: 'Olá {{contact.name}}, sua fatura...' },
    ],
    send_telegram: [
      { key: 'chat_id', label: 'Chat ID', placeholder: 'opcional — usa o padrão da integração' },
      { key: 'text',    label: 'Mensagem', type: 'textarea' },
    ],
    send_slack:   [{ key: 'text', label: 'Mensagem', type: 'textarea', placeholder: 'Notificação para o canal Slack' }],
    send_discord: [{ key: 'text', label: 'Mensagem', type: 'textarea', placeholder: 'Notificação para o canal Discord' }],
    notify_team: [
      { key: 'title',       label: 'Título' },
      { key: 'description', label: 'Descrição', type: 'textarea' },
      { key: 'link',        label: 'Link (opcional)', placeholder: '/dashboard' },
    ],
    create_task: [
      { key: 'title', label: 'Título da tarefa' },
      { key: 'description', label: 'Detalhes', type: 'textarea' },
    ],
    call_webhook: [
      { key: 'url',     label: 'URL', placeholder: 'https://api.exemplo.com/webhook' },
      { key: 'method',  label: 'Método', placeholder: 'POST' },
    ],
    update_lead_stage: [
      { key: 'stage', label: 'Novo estágio', placeholder: 'qualified, proposal, closed_won...' },
    ],
    create_invoice: [
      { key: 'amount',      label: 'Valor (R$)',   type: 'number', placeholder: '100.00' },
      { key: 'description', label: 'Descrição',    placeholder: 'Cobrança gerada por automação' },
    ],
    ai_insight: [
      { key: 'prompt', label: 'Prompt para a IA', type: 'textarea',
        placeholder: 'Analise o lead {{lead.title}} e sugira próximos passos.' },
    ],
    append_sheet: [
      { key: 'spreadsheet_id', label: 'Spreadsheet ID' },
      { key: 'range',          label: 'Range', placeholder: 'Sheet1!A:Z' },
    ],
    /* Sem params: generate_report, sync_bank */
  };
  return map[actionId] || [];
}

function escAttr(s) {
  return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/"/g,'&quot;');
}

/* ══════════════════════════════════════════════════════════
   Contact autocomplete
   - Aciona em inputs com [data-autocomplete="contact-email"|"contact-phone"]
   - Suporta lista separada por vírgula (sugere apenas para o último item)
   - Setas ↑↓ + Enter + Tab + clique
══════════════════════════════════════════════════════════ */

let _acDropdown = null;
let _acActiveInput = null;
let _acSelectedIdx = 0;
let _acFiltered = [];

async function ensureContactsLoaded() {
  if (_contacts.length) return;
  try {
    const res = await vexxAPI.get('/api/crm/contacts');
    _contacts = res.data || [];
  } catch {}
}

function bindAutocomplete() {
  const inputs = document.querySelectorAll('[data-autocomplete]');
  inputs.forEach(input => {
    if (input.dataset.acBound) return;
    input.dataset.acBound = '1';

    input.addEventListener('focus',  () => { ensureContactsLoaded().then(() => acUpdate(input)); });
    input.addEventListener('input',  async () => { await ensureContactsLoaded(); acUpdate(input); });
    input.addEventListener('keydown', acKeydown);
    input.addEventListener('blur',   () => setTimeout(acClose, 150)); /* delay p/ permitir clique */
  });
}

function acGetSegment(input) {
  /* Retorna {start, end, text} do trecho atual entre vírgulas */
  const v = input.value;
  const cursor = input.selectionEnd ?? v.length;
  let start = 0;
  for (let i = cursor - 1; i >= 0; i--) {
    if (v[i] === ',' || v[i] === ';') { start = i + 1; break; }
  }
  let end = v.length;
  for (let i = cursor; i < v.length; i++) {
    if (v[i] === ',' || v[i] === ';') { end = i; break; }
  }
  return { start, end, text: v.slice(start, end).trim() };
}

function acUpdate(input) {
  const seg = acGetSegment(input);
  const q = seg.text.toLowerCase();

  /* Não sugere quando o trecho é uma variável Jinja completa */
  if (q.startsWith('{{') && q.endsWith('}}')) return acClose();

  const kind = input.dataset.autocomplete; /* contact-email | contact-phone */

  let pool = _contacts;
  if (kind === 'contact-email') {
    pool = pool.filter(c => c.email);
  } else if (kind === 'contact-phone') {
    pool = pool.filter(c => c.phone);
  }

  /* Filtra com qualquer quantidade de caracteres (inclusive 1 letra/número) */
  const filtered = q.length > 0
    ? pool.filter(c => {
        const blob = `${c.name || ''} ${c.email || ''} ${c.phone || ''} ${c.company || ''}`.toLowerCase();
        return blob.includes(q);
      })
    : pool;

  _acFiltered = filtered.slice(0, 15);
  _acActiveInput = input;
  _acSelectedIdx = 0;

  if (!_acFiltered.length) return acClose();
  acRender(input, kind, q);
}

function acRender(input, kind, query) {
  acClose();
  const rect = input.getBoundingClientRect();
  const dd = document.createElement('div');
  dd.id = 'ac-dropdown';
  dd.style.cssText = `
    position: fixed;
    top: ${rect.bottom + 4}px;
    left: ${rect.left}px;
    width: ${Math.max(rect.width, 280)}px;
    max-height: 280px; overflow-y: auto;
    background: var(--bg-3);
    border: 1px solid var(--border-md);
    border-radius: var(--r);
    box-shadow: var(--shadow-lg);
    z-index: 2000;
    padding: 4px;
    animation: dropdown-in 0.12s ease;
  `;

  const items = [];

  _acFiltered.forEach((c, idx) => {
    const value = kind === 'contact-email' ? c.email : c.phone;
    if (!value) return;
    const initials = (c.name || '?').split(' ').map(s => s[0]).slice(0,2).join('').toUpperCase();
    const subtitle = [c.email, c.company].filter(Boolean).join(' · ');
    items.push({
      kind: 'contact',
      value,
      html: `
        <div style="display:flex;align-items:center;gap:10px;width:100%">
          <div style="width:28px;height:28px;background:var(--surface-lg);border-radius:50%;display:grid;place-items:center;color:var(--text-muted);font-size:.7rem;font-weight:700;flex-shrink:0">${initials}</div>
          <div style="flex:1;min-width:0">
            <div style="font-size:.82rem;font-weight:500">${escAttr(c.name)}</div>
            <div style="font-size:.7rem;color:var(--text-faint);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escAttr(value)}${subtitle && subtitle !== value ? ' · ' + escAttr(subtitle) : ''}</div>
          </div>
        </div>`,
    });
  });

  if (!items.length) return;

  dd.innerHTML = items.map((it, i) => `
    <button type="button" class="ac-item" data-idx="${i}" data-value="${escAttr(it.value)}"
            style="display:block;width:100%;text-align:left;padding:8px 10px;background:none;border:none;border-radius:6px;cursor:pointer;color:var(--text);transition:background .1s">
      ${it.html}
    </button>
  `).join('');

  document.body.appendChild(dd);
  _acDropdown = dd;

  /* Hover + click handlers */
  dd.querySelectorAll('.ac-item').forEach(btn => {
    btn.addEventListener('mouseenter', () => {
      _acSelectedIdx = parseInt(btn.dataset.idx, 10);
      acRefreshHighlight();
    });
    btn.addEventListener('mousedown', (e) => {
      e.preventDefault(); /* impede o blur do input antes do click */
      acPick(btn.dataset.value);
    });
  });

  acRefreshHighlight();
  if (window.lucide) lucide.createIcons();
}

function acRefreshHighlight() {
  if (!_acDropdown) return;
  _acDropdown.querySelectorAll('.ac-item').forEach((el, i) => {
    el.style.background = i === _acSelectedIdx ? 'var(--surface-md)' : 'transparent';
  });
  const active = _acDropdown.querySelector(`.ac-item[data-idx="${_acSelectedIdx}"]`);
  if (active) active.scrollIntoView({ block: 'nearest' });
}

function acKeydown(e) {
  if (!_acDropdown) return;
  const items = _acDropdown.querySelectorAll('.ac-item');
  if (!items.length) return;

  if (e.key === 'ArrowDown') {
    e.preventDefault();
    _acSelectedIdx = (_acSelectedIdx + 1) % items.length;
    acRefreshHighlight();
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    _acSelectedIdx = (_acSelectedIdx - 1 + items.length) % items.length;
    acRefreshHighlight();
  } else if (e.key === 'Enter' || e.key === 'Tab') {
    const active = items[_acSelectedIdx];
    if (active) {
      e.preventDefault();
      acPick(active.dataset.value);
    }
  } else if (e.key === 'Escape') {
    e.preventDefault();
    acClose();
  }
}

function acPick(value) {
  if (!_acActiveInput) return;
  const input = _acActiveInput;
  const seg = acGetSegment(input);
  const before = input.value.slice(0, seg.start);
  const after  = input.value.slice(seg.end);

  /* Se já tem texto antes (lista) e o "before" não termina com ", ", normaliza */
  let prefix = before;
  if (prefix && !prefix.endsWith(', ') && !prefix.endsWith(',')) prefix = prefix.trimEnd() + ', ';
  if (prefix.endsWith(',')) prefix += ' ';

  /* Acrescenta vírgula no fim para facilitar adicionar próximo destinatário */
  const newValue = prefix + value + (after.startsWith(',') ? after : (after ? ', ' + after.trimStart() : ', '));
  input.value = newValue.replace(/,\s*$/, ', '); /* mantém vírgula final pra próximo */

  /* Posiciona cursor após o item inserido */
  const cursorPos = (prefix + value + ', ').length;
  input.setSelectionRange(cursorPos, cursorPos);

  /* Dispara onchange manualmente */
  input.dispatchEvent(new Event('change', { bubbles: true }));

  acClose();
  input.focus();
}

function acClose() {
  if (_acDropdown) {
    _acDropdown.remove();
    _acDropdown = null;
  }
  _acFiltered = [];
}


async function saveWorkflow(e) {
  e.preventDefault();
  const id = document.getElementById('wf-id').value;

  if (!_currentSteps.length) {
    return showToast('Adicione pelo menos uma ação.', 'error');
  }

  const payload = {
    name:        document.getElementById('wf-name').value.trim(),
    description: document.getElementById('wf-desc').value.trim(),
    trigger:     document.getElementById('wf-trigger').value,
    action:      _currentSteps[0].action,  /* legacy */
    config:      { steps: _currentSteps, stop_on_error: false },
  };

  try {
    if (id) await vexxAPI.put(`/api/automation/${id}`, payload);
    else    await vexxAPI.post('/api/automation', payload);
    showToast(id ? 'Automação atualizada' : 'Automação criada', 'success');
    closeModal('wf-modal');
    loadStats(); loadAutomations(); loadLogs();
  } catch (err) { showToast(err.message || 'Erro', 'error'); }
}

async function toggleWf(id) {
  try {
    await vexxAPI.request('PATCH', `/api/automation/${id}/toggle`);
    loadStats();
  } catch (err) { showToast(err.message || 'Erro', 'error'); }
}
async function runWf(id) {
  try { await vexxAPI.post(`/api/automation/${id}/run`, {}); showToast('Teste executado', 'success'); loadStats(); loadAutomations(); loadLogs(); }
  catch (err) { showToast(err.message || 'Erro', 'error'); }
}
async function deleteWf(id) {
  if (!confirm('Remover esta automação?')) return;
  try { await vexxAPI.delete(`/api/automation/${id}`); showToast('Removida', 'success'); loadStats(); loadAutomations(); }
  catch (err) { showToast(err.message || 'Erro', 'error'); }
}

/* ── 2. Integrações ────────────────────────────────────── */
async function loadIntegrations() {
  const list = document.getElementById('connected-list');
  try {
    const res = await vexxAPI.get('/api/automation/integrations');
    _integrations = res.data || [];
    document.getElementById('kpi-integrations').textContent = _integrations.length;
    document.getElementById('tab-count-integrations').textContent = _integrations.length;

    if (!_integrations.length) {
      list.innerHTML = '<div style="padding:24px;text-align:center;color:var(--text-faint);font-size:.85rem">Nenhuma integração conectada. Escolha uma abaixo no marketplace.</div>';
      return;
    }

    list.innerHTML = `
      <div class="provider-grid">
        ${_integrations.map(i => `
          <div class="provider-card connected">
            <div class="provider-icon" style="background:${i.color}"><i data-lucide="${i.icon}" size="22"></i></div>
            <div class="provider-name">${esc(i.name)}</div>
            <div class="provider-desc">${esc(i.provider_name)} · ${i.status === 'connected' ? 'ativo' : i.status}</div>
            <div style="display:flex;gap:6px;margin-top:10px">
              <button class="btn-ghost btn-sm" onclick="testIntegration(${i.id})"><i data-lucide="check-circle" size="12"></i> Testar</button>
              <button class="btn-ghost btn-sm" onclick="disconnectIntegration(${i.id})" style="color:var(--red)"><i data-lucide="x" size="12"></i> Desconectar</button>
            </div>
          </div>`).join('')}
      </div>`;
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error(err);
    list.innerHTML = '<div style="color:var(--red);padding:16px">Erro ao carregar.</div>';
  }
}

async function loadProviders() {
  try {
    const res = await vexxAPI.get('/api/automation/integrations/providers');
    _providers  = res.data || [];
    _categories = res.categories || {};
    renderCategoryPills();
    renderProviderGrid();
  } catch {}
}

function renderCategoryPills() {
  const wrap = document.getElementById('category-pills');
  const cats = Object.entries(_categories);
  wrap.innerHTML =
    `<button class="cat-pill ${_selectedCat === 'all' ? 'active' : ''}" data-cat="all">Todos</button>` +
    cats.map(([id, c]) => `
      <button class="cat-pill ${_selectedCat === id ? 'active' : ''}" data-cat="${id}">${c.name}</button>
    `).join('');
  wrap.querySelectorAll('.cat-pill').forEach(p => {
    p.addEventListener('click', () => {
      _selectedCat = p.dataset.cat;
      renderCategoryPills();
      renderProviderGrid();
    });
  });
}

function renderProviderGrid() {
  const wrap = document.getElementById('provider-grid');
  const filtered = _selectedCat === 'all' ? _providers : _providers.filter(p => p.category === _selectedCat);
  const connectedSet = new Set(_integrations.map(i => i.provider));

  wrap.innerHTML = filtered.map(p => {
    const isConnected = connectedSet.has(p.id);
    return `
      <div class="provider-card ${isConnected ? 'connected' : ''}" onclick="${isConnected ? 'goTab(\'integrations\')' : `openConnectModal('${p.id}')`}">
        <div class="provider-icon" style="background:${p.color}"><i data-lucide="${p.icon}" size="22"></i></div>
        <div class="provider-name">${esc(p.name)}</div>
        <div class="provider-desc">${esc(p.description)}</div>
        ${isConnected ? '<div style="margin-top:10px;font-size:.72rem;color:var(--green);font-weight:600">✓ Conectado</div>' : `<div style="margin-top:10px;font-size:.72rem;color:var(--accent-light);font-weight:600">+ Conectar</div>`}
      </div>`;
  }).join('');
  if (window.lucide) lucide.createIcons();
}

async function openConnectModal(providerId) {
  /* Para Google providers: usa OAuth se configurado; senão cai no modal manual */
  const isGoogle = ['gmail', 'google_sheets', 'google_calendar'].includes(providerId);
  let oauthAvailable = false;

  if (isGoogle) {
    try {
      const status = await vexxAPI.get('/oauth/google/status');
      oauthAvailable = !!status.configured;
      if (oauthAvailable) {
        /* Google rejeita IPs privados — redireciona para localhost se necessário */
        const uid = window.__VEXX_USER__?.id || '';
        let oauthUrl = `/oauth/google/authorize?provider=${providerId}&uid=${uid}`;
        const host = window.location.hostname;
        if (/^(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)/.test(host)) {
          const port = window.location.port || '5000';
          oauthUrl = `http://localhost:${port}${oauthUrl}`;
        }
        window.location.href = oauthUrl;
        return;
      }
    } catch {}
    /* OAuth não configurado → segue para modal manual sem mostrar erro */
  }

  try {
    const res = await vexxAPI.get(`/api/automation/integrations/providers/${providerId}`);
    const p = res.data;
    document.getElementById('connect-modal-title').textContent = `Conectar ${p.name}`;

    /* Se Google sem OAuth, adiciona dica clara no início do form */
    let desc = p.description;
    if (isGoogle && !oauthAvailable) {
      desc = `${p.description}\n\n💡 Dica: para conectar com 1-clique via OAuth, defina GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET no .env do servidor. Caso contrário, cole o access token manualmente abaixo.`;
    }
    document.getElementById('connect-modal-desc').textContent = desc;
    document.getElementById('connect-modal-desc').style.whiteSpace = 'pre-wrap';

    document.getElementById('connect-provider').value = p.id;
    document.getElementById('connect-name').value     = p.name;

    const fields = document.getElementById('connect-fields');
    fields.innerHTML = (p.fields || []).map(f => {
      const placeholder = f.placeholder || '';
      const help = f.help ? `<p style="font-size:.7rem;color:var(--text-faint);margin-top:4px">${esc(f.help)}</p>` : '';
      if (f.type === 'select') {
        return `
          <div class="form-group">
            <label class="form-label">${esc(f.label)}${f.required ? ' *' : ''}</label>
            <select class="form-select" name="${f.key}" ${f.required ? 'required' : ''}>
              ${(f.options || []).map(o => `<option value="${o}" ${f.default === o ? 'selected' : ''}>${o}</option>`).join('')}
            </select>${help}
          </div>`;
      }
      if (f.type === 'checkbox') {
        return `
          <div class="form-group" style="display:flex;align-items:center;gap:10px">
            <input type="checkbox" id="cb-${f.key}" name="${f.key}" style="width:auto">
            <label for="cb-${f.key}" style="margin:0;cursor:pointer">${esc(f.label)}</label>${help}
          </div>`;
      }
      if (f.type === 'textarea') {
        return `<div class="form-group"><label class="form-label">${esc(f.label)}${f.required ? ' *' : ''}</label><textarea class="form-textarea" name="${f.key}" placeholder="${placeholder}" ${f.required ? 'required' : ''}></textarea>${help}</div>`;
      }
      return `<div class="form-group"><label class="form-label">${esc(f.label)}${f.required ? ' *' : ''}</label><input type="${f.type}" class="form-input" name="${f.key}" placeholder="${placeholder}" ${f.required ? 'required' : ''} autocomplete="off">${help}</div>`;
    }).join('');

    openModal('connect-modal');
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    showToast('Erro ao abrir formulário', 'error');
  }
}

async function saveConnection(e) {
  e.preventDefault();
  const provider = document.getElementById('connect-provider').value;
  const name     = document.getElementById('connect-name').value.trim();

  const credentials = {};
  document.querySelectorAll('#connect-fields [name]').forEach(input => {
    if (input.type === 'checkbox') credentials[input.name] = input.checked;
    else credentials[input.name] = input.value.trim();
  });

  try {
    await vexxAPI.post('/api/automation/integrations/connect', { provider, name, credentials });
    showToast(`${name} conectado!`, 'success');
    closeModal('connect-modal');
    loadIntegrations(); loadProviders();
  } catch (err) { showToast(err.message || 'Erro ao conectar', 'error'); }
}

async function testIntegration(id) {
  try { const res = await vexxAPI.post(`/api/automation/integrations/${id}/test`, {}); showToast(res.message || 'OK', 'success'); }
  catch (err) { showToast(err.message || 'Erro', 'error'); }
}
async function disconnectIntegration(id) {
  if (!confirm('Desconectar esta integração?')) return;
  try { await vexxAPI.delete(`/api/automation/integrations/${id}`); showToast('Desconectada', 'success'); loadIntegrations(); loadProviders(); }
  catch (err) { showToast(err.message || 'Erro', 'error'); }
}

/* ── 3. Templates ──────────────────────────────────────── */
async function loadTemplates() {
  const wrap = document.getElementById('templates-grid');
  try {
    const res = await vexxAPI.get('/api/automation/templates');
    const items = res.data || [];

    wrap.innerHTML = items.map(t => `
      <div class="widget-card" style="padding:16px;cursor:pointer;transition:all .15s" onclick="useTemplate('${t.id}')">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
          <div style="width:34px;height:34px;background:var(--accent-soft);border-radius:var(--r-sm);display:grid;place-items:center;color:var(--accent-light)">
            <i data-lucide="${t.icon}" size="16"></i>
          </div>
          <div style="font-weight:600;font-size:.88rem">${esc(t.name)}</div>
        </div>
        <p style="font-size:.78rem;color:var(--text-muted);line-height:1.5;margin-bottom:10px">${esc(t.description)}</p>
        <div style="display:flex;gap:4px;flex-wrap:wrap">
          ${(t.tags || []).map(tag => `<span class="badge badge-muted" style="font-size:.64rem">${tag}</span>`).join('')}
        </div>
      </div>`).join('');
    if (window.lucide) lucide.createIcons();
  } catch {}
}

async function useTemplate(id) {
  try {
    await vexxAPI.post(`/api/automation/templates/${id}/use`, {});
    showToast('Template aplicado!', 'success');
    goTab('workflows');
    loadStats(); loadAutomations(); loadLogs();
  } catch (err) { showToast(err.message || 'Erro', 'error'); }
}

/* ── 4. Sugestões IA ───────────────────────────────────── */
async function loadSuggestions() {
  const wrap = document.getElementById('suggestions-list');
  try {
    const res = await vexxAPI.get('/api/automation/suggestions');
    const items = res.data || [];

    if (!items.length) {
      wrap.innerHTML = '<div style="padding:24px;text-align:center;color:var(--text-faint)">Sem sugestões no momento.</div>';
      return;
    }

    const colorMap = {
      red:    'var(--red-soft)',  amber: 'var(--amber-soft)',
      blue:   'var(--blue-soft)', purple: 'var(--purple-soft)',
      green:  'var(--green-soft)', cyan: 'var(--cyan-soft)',
    };
    const iconColor = {
      red: 'var(--red)', amber: 'var(--amber)', blue: 'var(--blue)',
      purple: 'var(--purple)', green: 'var(--green)', cyan: 'var(--cyan)',
    };

    wrap.innerHTML = items.map(s => `
      <div class="sug-card priority-${s.priority}">
        <div class="sug-icon" style="background:${colorMap[s.color] || 'var(--accent-soft)'}">
          <i data-lucide="${s.icon}" size="16" style="color:${iconColor[s.color] || 'var(--accent-light)'}"></i>
        </div>
        <div>
          <div style="font-weight:600;font-size:.92rem;margin-bottom:4px">${esc(s.title)}</div>
          <div style="font-size:.8rem;color:var(--text-muted);line-height:1.5">${esc(s.description)}</div>
        </div>
        <button class="btn btn-primary btn-sm" onclick="useTemplate('${s.template_id}')">
          <i data-lucide="plus" size="12"></i> Criar
        </button>
      </div>`).join('');
    if (window.lucide) lucide.createIcons();
  } catch {
    wrap.innerHTML = '<div style="color:var(--red);padding:16px">Erro ao carregar sugestões.</div>';
  }
}

/* ── 5. Logs ───────────────────────────────────────────── */
async function loadLogs() {
  const wrap = document.getElementById('logs-list');
  const status = document.getElementById('log-filter')?.value || '';
  try {
    const res = await vexxAPI.get(`/api/automation/logs?status=${status}&limit=100`);
    const items = res.data || [];

    if (!items.length) {
      wrap.innerHTML = '<div style="padding:30px;text-align:center;color:var(--text-faint);font-size:.85rem">Sem execuções ainda. Crie ou execute uma automação para ver logs aqui.</div>';
      return;
    }

    const statusIcon = {
      success: '<i data-lucide="check-circle" size="13" style="color:var(--green)"></i> sucesso',
      error:   '<i data-lucide="x-circle" size="13" style="color:var(--red)"></i> erro',
      skipped: '<i data-lucide="minus-circle" size="13" style="color:var(--text-faint)"></i> pulado',
      pending: '<i data-lucide="clock" size="13" style="color:var(--amber)"></i> pendente',
    };

    wrap.innerHTML = items.map(l => `
      <div class="log-row">
        <span class="log-status-${l.status}" style="display:flex;align-items:center;gap:5px;font-size:.78rem">${statusIcon[l.status] || l.status}</span>
        <span style="color:var(--text)">${esc(l.message)}</span>
        <span style="font-size:.76rem;color:var(--text-faint)">${esc(l.trigger || '—')} → ${esc(l.action || '—')}</span>
        <span style="text-align:right;font-size:.76rem;color:var(--text-faint)">${formatDate(l.created_at)}</span>
      </div>`).join('');
    if (window.lucide) lucide.createIcons();
  } catch {
    wrap.innerHTML = '<div style="color:var(--red);padding:16px">Erro ao carregar logs.</div>';
  }
}

/* ── 6. Webhooks ──────────────────────────────────────── */
function setupWebhooks() {
  const userId = window.__VEXX_USER__?.id;
  const el = document.getElementById('webhook-base-url');
  if (!el) return;
  if (userId) {
    el.textContent = `${window.location.origin}/webhooks/${userId}/{event}`;
    return;
  }
  vexxAPI.get('/api/auth/me')
    .then(res => {
      const id = res.data?.id || '<seu_id>';
      el.textContent = `${window.location.origin}/webhooks/${id}/{event}`;
    })
    .catch(() => {
      el.textContent = `${window.location.origin}/webhooks/<seu_id>/{event}`;
    });
}

/* ── Helpers ──────────────────────────────────────────── */
function esc(s) {
  return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
