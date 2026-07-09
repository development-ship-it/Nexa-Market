// Dashboard-specific JS

document.addEventListener('DOMContentLoaded', () => {
  initTabSwitcher();
  animateBars();
});

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
