// Main JS entry — initializes shared behavior

document.addEventListener('DOMContentLoaded', () => {
  initSidebar();
  initCurrentDate();
  initChips();
  initAlertDismiss();
});

function initSidebar() {
  const sidebar = document.getElementById('sidebar');
  const toggleBtn = document.getElementById('sidebarToggle');
  const toggleMobile = document.getElementById('sidebarToggleMobile');
  const overlay = document.getElementById('sidebarOverlay');

  if (!sidebar) return;

  // Desktop collapse
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
      localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
    });
    if (localStorage.getItem('sidebarCollapsed') === 'true') {
      sidebar.classList.add('collapsed');
    }
  }

  // Mobile open/close
  function openSidebar() {
    sidebar.classList.add('open');
    overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
  }
  function closeSidebar() {
    sidebar.classList.remove('open');
    overlay.classList.remove('show');
    document.body.style.overflow = '';
  }

  if (toggleMobile) toggleMobile.addEventListener('click', openSidebar);
  if (overlay) overlay.addEventListener('click', closeSidebar);
}

function initCurrentDate() {
  const el = document.getElementById('currentDate');
  if (!el) return;
  const now = new Date();
  el.textContent = now.toLocaleDateString('es-CL', { weekday: 'short', day: 'numeric', month: 'short' });
}

function initChips() {
  document.querySelectorAll('[data-filter]').forEach(chip => {
    chip.addEventListener('click', () => {
      const group = chip.closest('.filter-chips');
      if (!group) return;
      group.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
    });
  });
}

function initAlertDismiss() {
  document.querySelectorAll('.alert').forEach(alert => {
    setTimeout(() => {
      alert.style.opacity = '0';
      alert.style.transition = 'opacity 0.4s';
      setTimeout(() => alert.remove(), 400);
    }, 4000);
  });
}

function formatCLP(value) {
  return '$' + Number(value).toLocaleString('es-CL');
}
