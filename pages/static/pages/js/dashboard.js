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
  const bars = document.querySelectorAll('.chart-bar-col');
  bars.forEach((bar, i) => {
    setTimeout(() => {
      bar.style.opacity = '1';
    }, i * 60);
  });
}
