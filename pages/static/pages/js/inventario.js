// Inventory page JS

document.addEventListener('DOMContentLoaded', () => {
  initSearch();
  initFilterChips();
});

function initSearch() {
  const input = document.getElementById('searchInput');
  if (!input) return;
  input.addEventListener('input', () => {
    const term = input.value.toLowerCase();
    document.querySelectorAll('.inv-card').forEach(card => {
      const name = card.querySelector('.inv-name')?.textContent.toLowerCase() || '';
      card.style.display = name.includes(term) ? '' : 'none';
    });
  });
}

function initFilterChips() {
  const chips = document.querySelectorAll('#filterChips .chip');
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      chips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      const filter = chip.dataset.filter;
      document.querySelectorAll('.inv-card').forEach(card => {
        if (filter === 'all') { card.style.display = ''; return; }
        const badge = card.querySelector('.inv-badge');
        const show = badge && badge.classList.contains(filter === 'zero' ? 'zero' : filter === 'low' ? 'low' : 'ok');
        card.style.display = show ? '' : 'none';
      });
    });
  });
}
