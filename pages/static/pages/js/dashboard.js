// Dashboard-specific JS

document.addEventListener('DOMContentLoaded', () => {
  initTabSwitcher();
  animateBars();
});

// Nota: el refresco automático se retiró a propósito. Ahora la app trabaja
// con el caché del navegador y el botón Sync del topbar (sync.js) avisa
// cuando hay datos nuevos, en vez de traer la página entera cada minuto.

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
