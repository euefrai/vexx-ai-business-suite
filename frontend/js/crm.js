/* ══════════════════════════════════════════════════════════
   VEXX AI — CRM page (Contatos + Pipeline)
══════════════════════════════════════════════════════════ */

const STAGE_LABEL = {
  prospect: 'Prospecção', qualified: 'Qualificado', proposal: 'Proposta',
  negotiation: 'Negociação', closed_won: 'Ganho', closed_lost: 'Perdido',
};
const STAGES = ['prospect', 'qualified', 'proposal', 'negotiation', 'closed_won', 'closed_lost'];
const STATUS_BADGE = {
  active:   '<span class="badge badge-green">Ativo</span>',
  inactive: '<span class="badge badge-muted">Inativo</span>',
  lead:     '<span class="badge badge-amber">Lead</span>',
};

let _contacts = [];

document.addEventListener('DOMContentLoaded', () => {
  loadContacts();
  loadPipeline();
  loadStats();
});

/* ── Tab switching ── */
function showTab(name) {
  document.getElementById('tab-contacts').classList.toggle('active', name === 'contacts');
  document.getElementById('tab-pipeline').classList.toggle('active', name === 'pipeline');
  document.getElementById('section-contacts').style.display = name === 'contacts' ? '' : 'none';
  document.getElementById('section-pipeline').style.display = name === 'pipeline' ? '' : 'none';
  if (name === 'pipeline') loadPipeline();
}

/* ── Stats ── */
async function loadStats() {
  try {
    const [stats, pipe] = await Promise.all([
      vexxAPI.get('/api/dashboard/stats'),
      vexxAPI.get('/api/crm/pipeline'),
    ]);
    const d = stats.data;
    document.getElementById('stat-contacts').textContent = formatNumber(d.total_contacts || 0);
    document.getElementById('stat-leads').textContent    = formatNumber(d.active_leads || 0);
    document.getElementById('stat-value').textContent    = formatBRL(d.leads_pipeline_value || 0);

    const won  = (pipe.data || []).find(s => s.stage === 'closed_won')?.count || 0;
    const lost = (pipe.data || []).find(s => s.stage === 'closed_lost')?.count || 0;
    const total = (pipe.data || []).reduce((s, x) => s + x.count, 0);
    const conv = total ? Math.round((won / total) * 100) : 0;

    document.getElementById('stat-won').textContent  = formatNumber(won);
    document.getElementById('stat-conv').textContent = `${conv}%`;
  } catch {}
}

/* ── Contacts list ── */
async function loadContacts() {
  const tbody  = document.getElementById('contacts-body');
  const search = document.getElementById('search-contacts').value;
  const status = document.getElementById('filter-status').value;

  try {
    const res = await vexxAPI.get(`/api/crm/contacts?search=${encodeURIComponent(search)}&status=${status}`);
    _contacts = res.data || [];

    if (!_contacts.length) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-faint);padding:30px">Nenhum contato encontrado.</td></tr>';
      return;
    }

    tbody.innerHTML = _contacts.map(c => `
      <tr>
        <td><strong style="color:var(--text)">${esc(c.name)}</strong>${c.position ? `<div style="font-size:.72rem;color:var(--text-faint)">${esc(c.position)}</div>` : ''}</td>
        <td>${esc(c.email || '—')}</td>
        <td>${esc(c.company || '—')}</td>
        <td>${STATUS_BADGE[c.status] || ''}</td>
        <td>
          <button class="btn-ghost btn-icon btn-sm" title="Editar" onclick='editContact(${c.id})'><i data-lucide="edit-2" size="13"></i></button>
          <button class="btn-ghost btn-icon btn-sm" title="Remover" onclick='deleteContact(${c.id})' style="color:var(--red)"><i data-lucide="trash-2" size="13"></i></button>
        </td>
      </tr>`).join('');

    if (window.lucide) lucide.createIcons();
    populateContactSelect();
  } catch {
    tbody.innerHTML = '<tr><td colspan="5" style="color:var(--red);padding:20px">Erro ao carregar contatos.</td></tr>';
  }
}

function populateContactSelect() {
  const sel = document.getElementById('lead-contact');
  if (!sel) return;
  const cur = sel.value;
  sel.innerHTML = '<option value="">— Nenhum —</option>' +
    _contacts.map(c => `<option value="${c.id}">${esc(c.name)}${c.company ? ' (' + esc(c.company) + ')' : ''}</option>`).join('');
  sel.value = cur;
}

/* ── Contact modal ── */
function openContactModal() {
  document.getElementById('contact-modal-title').textContent = 'Novo Contato';
  ['contact-id','contact-name','contact-email','contact-phone','contact-company','contact-position','contact-notes']
    .forEach(id => document.getElementById(id).value = '');
  document.getElementById('contact-status').value = 'active';
  openModal('contact-modal');
}

function editContact(id) {
  const c = _contacts.find(x => x.id === id);
  if (!c) return;
  document.getElementById('contact-modal-title').textContent = 'Editar Contato';
  document.getElementById('contact-id').value       = c.id;
  document.getElementById('contact-name').value     = c.name || '';
  document.getElementById('contact-email').value    = c.email || '';
  document.getElementById('contact-phone').value    = c.phone || '';
  document.getElementById('contact-company').value  = c.company || '';
  document.getElementById('contact-position').value = c.position || '';
  document.getElementById('contact-status').value   = c.status || 'active';
  document.getElementById('contact-notes').value    = c.notes || '';
  openModal('contact-modal');
}

async function saveContact(e) {
  e.preventDefault();
  const id = document.getElementById('contact-id').value;
  const payload = {
    name:     document.getElementById('contact-name').value.trim(),
    email:    document.getElementById('contact-email').value.trim(),
    phone:    document.getElementById('contact-phone').value.trim(),
    company:  document.getElementById('contact-company').value.trim(),
    position: document.getElementById('contact-position').value.trim(),
    status:   document.getElementById('contact-status').value,
    notes:    document.getElementById('contact-notes').value.trim(),
  };
  try {
    if (id) await vexxAPI.put(`/api/crm/contacts/${id}`, payload);
    else    await vexxAPI.post('/api/crm/contacts', payload);
    showToast(id ? 'Contato atualizado' : 'Contato criado', 'success');
    closeModal('contact-modal');
    loadContacts();
    loadStats();
  } catch (err) {
    showToast(err.message || 'Erro ao salvar', 'error');
  }
}

async function deleteContact(id) {
  if (!confirm('Remover este contato?')) return;
  try {
    await vexxAPI.delete(`/api/crm/contacts/${id}`);
    showToast('Contato removido', 'success');
    loadContacts(); loadStats();
  } catch (err) { showToast(err.message || 'Erro', 'error'); }
}

/* ── Pipeline kanban ── */
let _leadsByStage = {};

async function loadPipeline() {
  const board = document.getElementById('pipeline-board');
  try {
    const res = await vexxAPI.get('/api/crm/leads');
    const leads = res.data || [];

    _leadsByStage = {};
    STAGES.forEach(s => _leadsByStage[s] = []);
    leads.forEach(l => {
      if (_leadsByStage[l.stage]) _leadsByStage[l.stage].push(l);
    });

    board.innerHTML = STAGES.map(stage => {
      const items = _leadsByStage[stage] || [];
      const total = items.reduce((s, l) => s + (l.value || 0), 0);
      return `
        <div class="pipeline-col">
          <div class="pipeline-col-header">
            <span class="pipeline-col-title">${STAGE_LABEL[stage]}</span>
            <span class="pipeline-col-count">${items.length}</span>
          </div>
          <div style="font-size:.75rem;color:var(--text-faint);margin-bottom:8px">${formatBRL(total)}</div>
          <div class="pipeline-leads">
            ${items.length ? items.map(l => leadCardHTML(l)).join('') : '<div style="font-size:.78rem;color:var(--text-faint);padding:12px;text-align:center">Vazio</div>'}
          </div>
        </div>`;
    }).join('');

    if (window.lucide) lucide.createIcons();
  } catch {
    board.innerHTML = '<p style="color:var(--red)">Erro ao carregar pipeline.</p>';
  }
}

function leadCardHTML(l) {
  const idx = STAGES.indexOf(l.stage);
  const canAdvance = idx >= 0 && idx < STAGES.length - 2; /* don't auto-advance won/lost */
  return `
    <div class="pipeline-lead-card">
      <div style="display:flex;justify-content:space-between;gap:8px;align-items:flex-start">
        <div style="flex:1;min-width:0">
          <div class="pipeline-lead-title" title="${esc(l.title)}">${esc(l.title)}</div>
          <div class="pipeline-lead-value">${formatBRL(l.value || 0)} · ${l.probability || 0}%</div>
        </div>
        <div style="display:flex;gap:2px">
          <button class="btn-ghost btn-icon btn-sm" onclick='editLead(${l.id})' title="Editar"><i data-lucide="edit-2" size="11"></i></button>
          <button class="btn-ghost btn-icon btn-sm" onclick='deleteLead(${l.id})' title="Remover" style="color:var(--red)"><i data-lucide="trash-2" size="11"></i></button>
        </div>
      </div>
      <div style="display:flex;gap:4px;margin-top:8px">
        ${idx > 0 ? `<button class="btn-ghost btn-sm" onclick='moveLead(${l.id},"${STAGES[idx-1]}")'><i data-lucide="arrow-left" size="11"></i></button>` : ''}
        ${canAdvance ? `<button class="btn-ghost btn-sm" onclick='moveLead(${l.id},"${STAGES[idx+1]}")' style="margin-left:auto">${STAGE_LABEL[STAGES[idx+1]]} <i data-lucide="arrow-right" size="11"></i></button>` : ''}
        ${l.stage !== 'closed_won' && l.stage !== 'closed_lost' ? `
          <button class="btn-ghost btn-sm" onclick='moveLead(${l.id},"closed_won")' style="color:var(--green);margin-left:auto" title="Marcar ganho"><i data-lucide="check" size="11"></i></button>
          <button class="btn-ghost btn-sm" onclick='moveLead(${l.id},"closed_lost")' style="color:var(--red)" title="Marcar perdido"><i data-lucide="x" size="11"></i></button>` : ''}
      </div>
    </div>`;
}

async function moveLead(id, newStage) {
  try {
    await vexxAPI.request('PATCH', `/api/crm/leads/${id}/stage`, { stage: newStage });
    showToast(`Movido para ${STAGE_LABEL[newStage]}`, 'success');
    loadPipeline(); loadStats();
  } catch (err) { showToast(err.message || 'Erro', 'error'); }
}

function openLeadModal() {
  document.getElementById('lead-modal-title').textContent = 'Novo Lead';
  ['lead-id','lead-title','lead-value','lead-notes'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('lead-probability').value = 50;
  document.getElementById('lead-stage').value = 'prospect';
  document.getElementById('lead-contact').value = '';
  populateContactSelect();
  openModal('lead-modal');
}

function editLead(id) {
  const all = Object.values(_leadsByStage).flat();
  const l = all.find(x => x.id === id);
  if (!l) return;
  document.getElementById('lead-modal-title').textContent = 'Editar Lead';
  document.getElementById('lead-id').value          = l.id;
  document.getElementById('lead-title').value       = l.title || '';
  document.getElementById('lead-value').value       = l.value || 0;
  document.getElementById('lead-probability').value = l.probability || 50;
  document.getElementById('lead-stage').value       = l.stage || 'prospect';
  document.getElementById('lead-contact').value     = l.contact_id || '';
  document.getElementById('lead-notes').value       = l.notes || '';
  populateContactSelect();
  document.getElementById('lead-contact').value     = l.contact_id || '';
  openModal('lead-modal');
}

async function saveLead(e) {
  e.preventDefault();
  const id = document.getElementById('lead-id').value;
  const contactId = document.getElementById('lead-contact').value;
  const payload = {
    title:       document.getElementById('lead-title').value.trim(),
    value:       parseFloat(document.getElementById('lead-value').value || 0),
    probability: parseInt(document.getElementById('lead-probability').value || 50, 10),
    stage:       document.getElementById('lead-stage').value,
    contact_id:  contactId ? parseInt(contactId, 10) : null,
    notes:       document.getElementById('lead-notes').value.trim(),
  };
  try {
    if (id) await vexxAPI.put(`/api/crm/leads/${id}`, payload);
    else    await vexxAPI.post('/api/crm/leads', payload);
    showToast(id ? 'Lead atualizado' : 'Lead criado', 'success');
    closeModal('lead-modal');
    loadPipeline(); loadStats();
  } catch (err) {
    showToast(err.message || 'Erro ao salvar', 'error');
  }
}

async function deleteLead(id) {
  if (!confirm('Remover este lead?')) return;
  try {
    await vexxAPI.delete(`/api/crm/leads/${id}`);
    showToast('Lead removido', 'success');
    loadPipeline(); loadStats();
  } catch (err) { showToast(err.message || 'Erro', 'error'); }
}

/* ── Helpers ── */
function esc(str) {
  return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
