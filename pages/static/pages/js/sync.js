// Sincronización estilo AppSheet.
//
// La app trabaja con los datos guardados en el navegador (Service Worker).
// Cada minuto se consulta una firma minúscula del estado de la empresa; si
// cambió respecto a la última sincronización, el botón Sync se enciende.
// Al pulsarlo se vacía el caché de páginas y se recargan los datos frescos.

(function () {
  'use strict';

  const API     = '/api/estado/';
  const POLL_MS = 60000;

  let btn, texto, usuarioId = null;

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  }

  document.addEventListener('DOMContentLoaded', init);

  function init() {
    btn = document.getElementById('syncBtn');
    if (!btn) return;
    texto = btn.querySelector('.sync-text');

    btn.addEventListener('click', sincronizar);

    // Tras enviar un formulario, los datos nuevos son nuestros: no avisar de "cambios"
    document.addEventListener('submit', () => {
      guardar('nm_sync_escritura', '1', sessionStorage);
    }, true);

    // Al cerrar sesión se vacía todo: en un equipo compartido nadie debe ver
    // páginas cacheadas de la sesión anterior.
    document.querySelectorAll('form[action*="/logout/"]').forEach(f => {
      f.addEventListener('submit', (ev) => {
        if (f.dataset.purgado) return;          // 2.º submit: ya purgamos, dejar pasar
        ev.preventDefault();
        purgar('PURGAR_TODO').then(() => {
          f.dataset.purgado = '1';
          f.submit();
        });
      });
    });

    comprobar(true);
    setInterval(() => comprobar(false), POLL_MS);
    window.addEventListener('online',  () => comprobar(false));
    window.addEventListener('offline', () => pintar('offline'));
  }

  // ── Almacenamiento (tolerante a modo privado) ──────────────────────────────

  function guardar(k, v, almacen) {
    try { (almacen || localStorage).setItem(k, v); } catch (e) {}
  }
  function leer(k, almacen) {
    try { return (almacen || localStorage).getItem(k); } catch (e) { return null; }
  }
  function claveBase() { return 'nm_sync_base_' + usuarioId; }

  // ── Comprobación de cambios ───────────────────────────────────────────────

  async function comprobar(esCarga) {
    if (!navigator.onLine) { pintar('offline'); return; }
    let datos;
    try {
      const r = await fetch(API, { credentials: 'same-origin', cache: 'no-store' });
      if (!r.ok) return;
      datos = await r.json();
    } catch (e) {
      pintar('offline');
      return;
    }

    // Cambió el usuario logueado: el caché anterior no le pertenece
    const previo = leer('nm_sync_usuario');
    if (previo !== null && previo !== String(datos.usuario)) {
      await purgar('PURGAR_TODO');
    }
    usuarioId = datos.usuario;
    guardar('nm_sync_usuario', String(usuarioId));

    // Si venimos de guardar algo nosotros, la referencia se pone al día
    let escrituraPropia = false;
    if (esCarga && leer('nm_sync_escritura', sessionStorage) === '1') {
      escrituraPropia = true;
      try { sessionStorage.removeItem('nm_sync_escritura'); } catch (e) {}
    }

    if (!leer(claveBase()) || escrituraPropia) {
      fijarBase(datos.firma);
    }
    pintar(datos.firma === leer(claveBase()) ? 'ok' : 'cambios');
  }

  function fijarBase(firma) {
    guardar(claveBase(), firma);
    guardar('nm_sync_ts', String(Date.now()));
  }

  // ── Botón ─────────────────────────────────────────────────────────────────

  function pintar(estado) {
    if (!btn) return;
    btn.classList.remove('is-stale', 'is-offline', 'is-syncing');
    if (estado === 'cambios') {
      btn.classList.add('is-stale');
      texto.textContent = 'Hay cambios';
      btn.title = 'Hay datos nuevos en el servidor — pulsa para sincronizar';
    } else if (estado === 'offline') {
      btn.classList.add('is-offline');
      texto.textContent = 'Sin conexión';
      btn.title = 'Trabajando con los datos guardados en este dispositivo';
    } else {
      texto.textContent = 'Al día';
      btn.title = 'Datos sincronizados' + desde() + ' — pulsa para actualizar';
    }
  }

  function desde() {
    const ts = parseInt(leer('nm_sync_ts') || '0', 10);
    if (!ts) return '';
    const min = Math.floor((Date.now() - ts) / 60000);
    if (min < 1) return ' hace instantes';
    if (min < 60) return ' hace ' + min + ' min';
    return ' hace ' + Math.floor(min / 60) + ' h';
  }

  // ── Sincronizar ───────────────────────────────────────────────────────────

  async function sincronizar() {
    btn.classList.add('is-syncing');
    texto.textContent = 'Sincronizando…';

    await purgar('PURGAR');
    try {
      const r = await fetch(API, { credentials: 'same-origin', cache: 'no-store' });
      if (r.ok) fijarBase((await r.json()).firma);
    } catch (e) {}

    location.reload();
  }

  // Pide al Service Worker que vacíe el caché y espera su confirmación
  function purgar(tipo) {
    return new Promise((resolve) => {
      const sw = navigator.serviceWorker && navigator.serviceWorker.controller;
      if (!sw) return resolve();
      const canal = new MessageChannel();
      canal.port1.onmessage = () => resolve();
      try { sw.postMessage({ tipo: tipo }, [canal.port2]); } catch (e) { return resolve(); }
      setTimeout(resolve, 1500);  // no bloquear si el SW no contesta
    });
  }
})();
