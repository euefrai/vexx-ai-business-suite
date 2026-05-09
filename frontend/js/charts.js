/* ══════════════════════════════════════════════════════════
   VEXX AI — Chart.js Configurations
══════════════════════════════════════════════════════════ */

let revenueChart = null;

const CHART_DEFAULTS = {
  font: { family: "'Inter', sans-serif" },
  color: 'rgba(255,255,255,0.35)',
};

Chart.defaults.font.family = CHART_DEFAULTS.font.family;
Chart.defaults.color       = CHART_DEFAULTS.color;

/* ── Revenue Chart ──────────────────────────────────────── */
function initRevenueChart(data = null) {
  const ctx = document.getElementById('revenue-chart');
  if (!ctx) return;

  const labels   = data?.labels   || ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'];
  const revenue  = data?.revenue  || [0, 0, 0, 0, 0, 0];
  const expenses = data?.expenses || [0, 0, 0, 0, 0, 0];
  const profit   = revenue.map((r, i) => r - expenses[i]);

  if (revenueChart) revenueChart.destroy();

  revenueChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Receita',
          data: revenue,
          backgroundColor: 'rgba(16,185,129,0.75)',
          borderColor: 'rgba(16,185,129,1)',
          borderWidth: 0,
          borderRadius: 6,
          borderSkipped: false,
        },
        {
          label: 'Despesas',
          data: expenses,
          backgroundColor: 'rgba(244,63,94,0.65)',
          borderColor: 'rgba(244,63,94,1)',
          borderWidth: 0,
          borderRadius: 6,
          borderSkipped: false,
        },
        {
          label: 'Lucro',
          data: profit,
          type: 'line',
          borderColor: 'rgba(59,130,246,0.7)',
          backgroundColor: 'rgba(59,130,246,0.08)',
          borderWidth: 2,
          pointRadius: 3,
          pointBackgroundColor: 'rgba(59,130,246,0.9)',
          tension: 0.4,
          fill: true,
          yAxisID: 'y',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(12,12,24,0.95)',
          borderColor: 'rgba(255,255,255,0.08)',
          borderWidth: 1,
          padding: 12,
          titleFont: { size: 12, weight: '600' },
          bodyFont: { size: 12 },
          callbacks: {
            label(ctx) {
              return ` ${ctx.dataset.label}: ${formatBRL(ctx.raw)}`;
            },
          },
        },
      },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.04)', drawBorder: false },
          ticks: { font: { size: 11 } },
        },
        y: {
          grid: { color: 'rgba(255,255,255,0.04)', drawBorder: false },
          ticks: {
            font: { size: 11 },
            callback(val) {
              if (val >= 1000) return `R$${(val / 1000).toFixed(0)}K`;
              return `R$${val}`;
            },
          },
        },
      },
    },
  });
}

/* ── Switch chart period ────────────────────────────────── */
function switchPeriod(btn, period) {
  document.querySelectorAll('.period-tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  loadChartData(period);
}

async function loadChartData(period = '6m') {
  try {
    const data = await vexxAPI.get(`/api/finance/chart?period=${period}`);
    initRevenueChart(data);
  } catch {
    initRevenueChart(null);
  }
}

/* ── Sparkline SVG helper ───────────────────────────────── */
function drawSparkline(polylineId, values) {
  const poly = document.getElementById(polylineId);
  if (!poly || !values?.length) return;

  const W = 80, H = 28, pad = 2;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const points = values.map((v, i) => {
    const x = pad + (i / (values.length - 1)) * (W - pad * 2);
    const y = H - pad - ((v - min) / range) * (H - pad * 2);
    return `${x},${y}`;
  }).join(' ');

  poly.setAttribute('points', points);
}
