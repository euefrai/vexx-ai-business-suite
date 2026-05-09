/* ══════════════════════════════════════════════════════════
   VEXX AI — Sidebar, Topbar & Command Palette
══════════════════════════════════════════════════════════ */

/* ── Collapse ───────────────────────────────────────────── */
function toggleCollapse() {
  const sidebar = document.getElementById('sidebar');
  sidebar.classList.toggle('collapsed');
  const collapsed = sidebar.classList.contains('collapsed');
  localStorage.setItem('sidebar_collapsed', collapsed ? '1' : '0');
}

/* ── Mobile sidebar ─────────────────────────────────────── */
function toggleMobileSidebar() {
  const sidebar  = document.getElementById('sidebar');
  const overlay  = document.getElementById('sidebar-overlay');
  const isOpen   = sidebar.classList.toggle('mobile-open');
  overlay.classList.toggle('active', isOpen);
}

/* ── Notifications panel ────────────────────────────────── */
function toggleNotifications() {
  const panel    = document.getElementById('notif-panel');
  const dropdown = document.getElementById('user-dropdown');
  dropdown?.classList.remove('open');
  panel?.classList.toggle('open');
}

/* ── User dropdown ──────────────────────────────────────── */
function toggleUserDropdown() {
  const dropdown = document.getElementById('user-dropdown');
  const panel    = document.getElementById('notif-panel');
  panel?.classList.remove('open');
  dropdown?.classList.toggle('open');
}

/* ── Close panels on outside click ─────────────────────── */
document.addEventListener('click', (e) => {
  const notifPanel = document.getElementById('notif-panel');
  const notifBtn   = document.getElementById('notif-btn');
  const dropdown   = document.getElementById('user-dropdown');
  const topbarUser = document.getElementById('topbar-user');
  const sidebarUser = document.getElementById('sidebar-user');

  if (notifPanel && !notifPanel.contains(e.target) && e.target !== notifBtn && !notifBtn?.contains(e.target)) {
    notifPanel.classList.remove('open');
  }

  if (dropdown && !dropdown.contains(e.target) && !topbarUser?.contains(e.target) && !sidebarUser?.contains(e.target)) {
    dropdown.classList.remove('open');
  }
});

/* ── Notifications loader (server-driven) ──────────────── */
async function loadNotifications() {
  const list = document.getElementById('notif-list');
  if (!list) return;

  try {
    const res = await vexxAPI.get('/api/notifications');
    const items = res.data || [];

    const dot = document.getElementById('notif-dot');
    if (dot) dot.style.display = res.unread > 0 ? '' : 'none';

    if (!items.length) {
      list.innerHTML = '<div style="padding:24px;text-align:center;color:var(--text-faint);font-size:.84rem">Sem notificações ainda.</div>';
      return;
    }

    const colors = {
      info: { bg: 'var(--blue-soft)',   c: 'var(--blue)',   icon: 'info' },
      success: { bg: 'var(--green-soft)', c: 'var(--green)', icon: 'check-circle' },
      warning: { bg: 'var(--amber-soft)', c: 'var(--amber)', icon: 'alert-triangle' },
      error:   { bg: 'var(--red-soft)',   c: 'var(--red)',   icon: 'alert-circle' },
      ai:      { bg: 'var(--accent-soft)', c: 'var(--accent-light)', icon: 'bot' },
      lead:    { bg: 'var(--amber-soft)', c: 'var(--amber)', icon: 'target' },
    };

    list.innerHTML = items.map(n => {
      const s = colors[n.type] || colors.info;
      return `
        <div class="notif-item ${!n.is_read ? 'unread' : ''}" onclick="markRead(${n.id}, '${n.link || ''}')">
          <div class="notif-icon" style="background:${s.bg}"><i data-lucide="${s.icon}" size="14" style="color:${s.c}"></i></div>
          <div class="notif-body">
            <p class="notif-title">${(n.title || '').replace(/</g,'&lt;')}</p>
            <p class="notif-desc">${(n.description || '').replace(/</g,'&lt;')}</p>
            <p class="notif-time">${formatRel(n.created_at)}</p>
          </div>
        </div>`;
    }).join('');
    if (window.lucide) lucide.createIcons();
  } catch {}
}

function formatRel(iso) {
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000);
  if (diff < 60)    return 'agora';
  if (diff < 3600)  return `${Math.floor(diff/60)} min atrás`;
  if (diff < 86400) return `${Math.floor(diff/3600)}h atrás`;
  return `${Math.floor(diff/86400)}d atrás`;
}

async function markRead(id, link) {
  try { await vexxAPI.request('PATCH', `/api/notifications/${id}/read`); } catch {}
  if (link) window.location.href = link;
  else loadNotifications();
}

async function markAllRead() {
  try {
    await vexxAPI.post('/api/notifications/read-all', {});
    loadNotifications();
  } catch {}
}

/* Auto-load notifications on page boot */
document.addEventListener('DOMContentLoaded', () => {
  if (typeof vexxAPI !== 'undefined') loadNotifications();
});

/* ── Command palette ────────────────────────────────────── */
const CMD_ITEMS = [
  { label: 'Dashboard',        href: '/dashboard',    icon: 'layout-dashboard' },
  { label: 'CRM — Contatos',   href: '/crm',          icon: 'users'           },
  { label: 'Financeiro',       href: '/finance',       icon: 'wallet'          },
  { label: 'Automação',        href: '/automation',    icon: 'zap'             },
  { label: 'IA Assistente',    href: '/ai-assistant',  icon: 'bot'             },
  { label: 'Analytics',        href: '/analytics',     icon: 'bar-chart-2'     },
  { label: 'Configurações',    href: '/settings',      icon: 'settings'        },
  { label: 'Billing',          href: '/billing',       icon: 'credit-card'     },
];

let cmdActiveIndex = 0;

function openCommandPalette() {
  const overlay = document.getElementById('cmd-overlay');
  const input   = document.getElementById('cmd-input');
  overlay.classList.add('open');
  setTimeout(() => input?.focus(), 50);
  renderCmdItems(CMD_ITEMS);
}

function closeCommandPalette() {
  document.getElementById('cmd-overlay').classList.remove('open');
  const input = document.getElementById('cmd-input');
  if (input) input.value = '';
  cmdActiveIndex = 0;
}

function filterCommands(query) {
  const q = query.toLowerCase().trim();
  const results = q ? CMD_ITEMS.filter(i => i.label.toLowerCase().includes(q)) : CMD_ITEMS;
  cmdActiveIndex = 0;
  renderCmdItems(results);
}

function renderCmdItems(items) {
  const container = document.getElementById('cmd-results');
  if (!container) return;

  if (!items.length) {
    container.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-faint);font-size:0.84rem">Nenhum resultado encontrado</div>';
    return;
  }

  container.innerHTML = `
    <div class="cmd-section-label">Navegação</div>
    ${items.map((item, i) => `
      <div class="cmd-item ${i === cmdActiveIndex ? 'active' : ''}" data-href="${item.href}" onclick="window.location.href='${item.href}'">
        <i data-lucide="${item.icon}" size="14"></i>
        ${item.label}
      </div>
    `).join('')}
  `;

  if (window.lucide) lucide.createIcons();
}

function cmdKeyDown(e) {
  const items = document.querySelectorAll('.cmd-item');
  if (!items.length) return;

  if (e.key === 'ArrowDown') {
    e.preventDefault();
    cmdActiveIndex = Math.min(cmdActiveIndex + 1, items.length - 1);
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    cmdActiveIndex = Math.max(cmdActiveIndex - 1, 0);
  } else if (e.key === 'Enter') {
    const active = items[cmdActiveIndex];
    if (active) window.location.href = active.dataset.href;
    return;
  } else if (e.key === 'Escape') {
    closeCommandPalette();
    return;
  }

  items.forEach((el, i) => el.classList.toggle('active', i === cmdActiveIndex));
  items[cmdActiveIndex]?.scrollIntoView({ block: 'nearest' });
}

/* ── Keyboard shortcut: Cmd/Ctrl+K ─────────────────────── */
document.addEventListener('keydown', (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault();
    const overlay = document.getElementById('cmd-overlay');
    overlay?.classList.contains('open') ? closeCommandPalette() : openCommandPalette();
  }
  if (e.key === 'Escape') {
    closeCommandPalette();
  }
});

/* ── Restore collapsed state ────────────────────────────── */
(function restoreCollapsed() {
  if (localStorage.getItem('sidebar_collapsed') === '1') {
    document.getElementById('sidebar')?.classList.add('collapsed');
  }
})();

/* ── Quick Add modal placeholder ───────────────────────── */
function openQuickAdd() {
  showToast('Ação rápida em breve!', 'info');
}
