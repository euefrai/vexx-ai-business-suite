/* ══════════════════════════════════════════════════════════
   VEXX AI — Auth Guard
   Runs before DOMContentLoaded on every protected page.
══════════════════════════════════════════════════════════ */

(async function guardAuth() {
  try {
    const res = await fetch('/api/auth/me', { credentials: 'include' });
    if (res.status === 401) {
      window.location.href = '/login';
    }
  } catch {
    window.location.href = '/login';
  }
})();
