// Dashboard-specific JS

document.addEventListener('DOMContentLoaded', () => {
  initTabSwitcher();
  animateBars();
  initAutoRefresh();
});

// Refresco en segundo plano cada 60 s: trae el HTML nuevo y reemplaza
// solo el contenido del dashboard, sin recargar la página ni mover el scroll.
function initAutoRefresh() {
  const REFRESH_MS = 60000;
  setInterval(async () => {
    if (document.hidden) return;  // pestaña en segundo plano: no gastar red
    try {
      const resp = await fetch(window.location.href, { credentials: 'same-origin' });
      if (!resp.ok) return;
      const doc = new DOMParser().parseFromString(await resp.text(), 'text/html');
      const nuevo = doc.querySelector('.dashboard-grid');
      const actual = document.querySelector('.dashboard-grid');
      if (nuevo && actual) {
        actual.innerHTML = nuevo.innerHTML;
        animateBars();
      }
    } catch (e) { /* sin conexión: se reintenta en el próximo ciclo */ }
  }, REFRESH_MS);
}

function initTabSwitcher() {
  document.querySelectorAll('.tab[data-period]').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab[data-period]').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      // Future: fetch data for period tab.dataset.period
    });
  });
}

function animateBars() {
  // Dibujado progresivo de la línea de ventas por hora
  const line = document.querySelector('.line-chart-svg polyline');
  if (line) {
    const len = line.getTotalLength ? line.getTotalLength() : 0;
    if (len) {
      line.style.transition = 'none';
      line.style.strokeDasharray = len;
      line.style.strokeDashoffset = len;
      // forzar reflow y animar
      void line.getBoundingClientRect();
      line.style.transition = 'stroke-dashoffset 1s ease';
      line.style.strokeDashoffset = '0';
    }
  }
  // Crecimiento de las barras de ranking (más vendidos)
  document.querySelectorAll('.rank-bar span').forEach((bar, i) => {
    const w = bar.style.width;
    bar.style.transition = 'none';
    bar.style.width = '0';
    void bar.getBoundingClientRect();
    setTimeout(() => {
      bar.style.transition = 'width .6s ease';
      bar.style.width = w;
    }, i * 50);
  });
}
