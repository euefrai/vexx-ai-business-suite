/* ══════════════════════════════════════════════════════════
   VEXX AI — API Client (CSRF-aware)
══════════════════════════════════════════════════════════ */

/* Lê o CSRF token do meta tag injetado em cada página */
function _csrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute('content') : '';
}

const vexxAPI = {
  async request(method, path, data = null) {
    const headers = { 'Content-Type': 'application/json' };

    /* CSRF: Flask-WTF aceita token em X-CSRFToken para qualquer método mutador */
    const upperMethod = method.toUpperCase();
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(upperMethod)) {
      const token = _csrfToken();
      if (token) headers['X-CSRFToken'] = token;
    }

    const opts = { method: upperMethod, headers, credentials: 'include' };
    if (data) opts.body = JSON.stringify(data);

    let res;
    try {
      res = await fetch(path, opts);
    } catch (e) {
      throw { status: 0, message: 'Sem conexão com o servidor.' };
    }

    /* CSRF expirou (token rotacionou): tenta atualizar e dá uma chance */
    if (res.status === 400) {
      const text = await res.clone().text();
      if (text.includes('CSRF') && !opts._retried) {
        try {
          const fresh = await fetch('/api/csrf', { credentials: 'include' });
          const j = await fresh.json();
          if (j.token) {
            const meta = document.querySelector('meta[name="csrf-token"]');
            if (meta) meta.setAttribute('content', j.token);
            opts._retried = true;
            opts.headers['X-CSRFToken'] = j.token;
            res = await fetch(path, opts);
          }
        } catch {}
      }
    }

    const json = await res.json().catch(() => ({}));
    if (!res.ok) {
      if (res.status === 401 && !window.location.pathname.startsWith('/login')) {
        window.location.href = '/login';
      }
      throw { status: res.status, message: json.error || json.message || 'Erro desconhecido' };
    }
    return json;
  },

  get:    (path)       => vexxAPI.request('GET',    path),
  post:   (path, data) => vexxAPI.request('POST',   path, data),
  put:    (path, data) => vexxAPI.request('PUT',    path, data),
  delete: (path)       => vexxAPI.request('DELETE', path),
};

/* ── Toast Notifications ────────────────────────────────── */
function showToast(message, type = 'info', duration = 3500) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const icons = { success: '✓', error: '✗', info: 'ℹ' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span style="font-size:1rem">${icons[type] || icons.info}</span> ${message}`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    toast.style.opacity    = '0';
    toast.style.transform  = 'translateX(12px)';
    setTimeout(() => toast.remove(), 320);
  }, duration);
}

/* ── Number formatting ──────────────────────────────────── */
function formatBRL(value) {
  if (value === null || value === undefined) return 'R$ 0';
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency', currency: 'BRL', minimumFractionDigits: 0, maximumFractionDigits: 0,
  }).format(value);
}

function formatNumber(value) {
  if (!value) return '0';
  return new Intl.NumberFormat('pt-BR').format(value);
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  return new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(new Date(dateStr));
}

function timeAgo(dateStr) {
  if (!dateStr) return '';
  const diff = Math.floor((Date.now() - new Date(dateStr)) / 1000);
  if (diff < 60)   return 'agora mesmo';
  if (diff < 3600) return `${Math.floor(diff / 60)} min atrás`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h atrás`;
  return `${Math.floor(diff / 86400)}d atrás`;
}

/* ── Counter animation ──────────────────────────────────── */
function animateCounter(el, target, formatter = (v) => v, duration = 900) {
  if (!el) return;
  const start = 0;
  const startTime = performance.now();

  function tick(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    el.textContent = formatter(Math.floor(start + (target - start) * ease));
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}
