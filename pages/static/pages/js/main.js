// Main JS entry — initializes shared behavior

document.addEventListener('DOMContentLoaded', () => {
  initSidebar();
  initCurrentDate();
  initChips();
  initAlertDismiss();
});

// Menú lateral: la flecha lo oculta (la pantalla se agranda) y la hamburguesa
// del topbar lo vuelve a mostrar. En móvil el menú se superpone con fondo.
function initSidebar() {
  const sidebar = document.getElementById('sidebar');
  const btnOcultar = document.getElementById('sidebarToggle');
  const btnMostrar = document.getElementById('sidebarToggleMobile');
  const overlay = document.getElementById('sidebarOverlay');

  if (!sidebar) return;

  const esMovil = () => window.matchMedia('(max-width: 768px)').matches;

  function abrirMovil() {
    sidebar.classList.add('open');
    if (overlay) overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
  }
  function cerrarMovil() {
    sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('show');
    document.body.style.overflow = '';
  }

  function ocultar() {
    if (esMovil()) { cerrarMovil(); return; }
    sidebar.classList.add('oculto');
    try { localStorage.setItem('sidebarOculto', 'true'); } catch (e) {}
  }
  function mostrar() {
    if (esMovil()) { abrirMovil(); return; }
    sidebar.classList.remove('oculto');
    try { localStorage.setItem('sidebarOculto', 'false'); } catch (e) {}
  }

  if (btnOcultar) btnOcultar.addEventListener('click', ocultar);
  if (btnMostrar) btnMostrar.addEventListener('click', mostrar);
  if (overlay) overlay.addEventListener('click', cerrarMovil);

  // Restaurar el estado elegido (solo en escritorio)
  try {
    if (localStorage.getItem('sidebarOculto') === 'true' && !esMovil()) {
      sidebar.classList.add('oculto');
    }
  } catch (e) {}

  // Al pasar de móvil a escritorio, limpiar el estado de superposición
  window.addEventListener('resize', () => {
    if (!esMovil() && sidebar.classList.contains('open')) cerrarMovil();
  });
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
