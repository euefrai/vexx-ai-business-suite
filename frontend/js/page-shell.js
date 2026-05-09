/* ══════════════════════════════════════════════════════════
   VEXX AI — Shared page shell loader
   Populates sidebar/topbar/dropdown user info on every inner page.
══════════════════════════════════════════════════════════ */

(async function loadPageShell() {
  try {
    const res  = await vexxAPI.get('/api/auth/me');
    const u    = res.data;
    const full = [u.first_name, u.last_name].filter(Boolean).join(' ');
    const init = ((u.first_name?.[0] || '') + (u.last_name?.[0] || '')).toUpperCase() || 'U';
    const planLabels = { free: 'Free', pro: 'Pro', enterprise: 'Enterprise' };

    const setText = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val ?? '—'; };
    setText('s-user-name', full);
    setText('s-user-company', u.company || 'Sem empresa');
    setText('t-user-name', u.first_name || 'Usuário');
    setText('d-user-name', full);
    setText('d-user-email', u.email || '');
    setText('topbar-plan-label', planLabels[u.plan] || 'Free');

    ['s-user-avi', 't-user-avi', 'd-user-avi'].forEach(id => setText(id, init));

    if (u.plan !== 'free') {
      document.getElementById('sidebar-upgrade')?.classList.add('hidden');
    }

    window.__VEXX_USER__ = u;
  } catch (err) {
    console.warn('page-shell auth load failed', err);
  }
})();

/* Generic modal helpers */
function openModal(id)  { document.getElementById(id)?.classList.add('open'); }
function closeModal(id) { document.getElementById(id)?.classList.remove('open'); }
