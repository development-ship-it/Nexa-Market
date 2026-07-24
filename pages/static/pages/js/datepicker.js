// Mini calendario propio — español, dd/mm/aaaa, tema oscuro. Sin librerías.
//
// Uso: un <input type="text" readonly data-iso="yyyy-mm-dd"
//            onclick="nmDatePicker.abrir(this)">
// Al elegir un día escribe input.dataset.iso (ISO, lo que espera el backend) y
// input.value (dd/mm/aaaa para mostrar), y dispara 'change'.
window.nmDatePicker = (function () {
  'use strict';

  const MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
  const DIAS = ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sá', 'Do'];

  let pop = null;      // el popup (uno solo, reutilizado por todos los campos)
  let input = null;    // input activo
  let anio, mes;       // mes que se está mostrando

  // ── Conversión de fechas ──
  function fmt(iso) {                       // 'yyyy-mm-dd' → 'dd/mm/aaaa'
    if (!iso) return '';
    const p = iso.split('-');
    return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : '';
  }
  function aISO(y, m, d) {                  // (2026, 7, 4) → '2026-07-04'
    return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
  }
  function hoyISO() {
    const n = new Date();
    return aISO(n.getFullYear(), n.getMonth() + 1, n.getDate());
  }

  // ── Construcción del popup (una vez) ──
  function crear() {
    pop = document.createElement('div');
    pop.className = 'nm-cal';
    pop.hidden = true;
    pop.innerHTML =
      '<div class="nm-cal-head">' +
        '<button type="button" class="nm-cal-nav" data-nav="-1" aria-label="Mes anterior">‹</button>' +
        '<span class="nm-cal-title"></span>' +
        '<button type="button" class="nm-cal-nav" data-nav="1" aria-label="Mes siguiente">›</button>' +
      '</div>' +
      '<div class="nm-cal-semana">' + DIAS.map(d => `<span>${d}</span>`).join('') + '</div>' +
      '<div class="nm-cal-grid"></div>' +
      '<div class="nm-cal-foot">' +
        '<button type="button" data-accion="hoy">Hoy</button>' +
        '<button type="button" data-accion="borrar">Borrar</button>' +
      '</div>';
    document.body.appendChild(pop);

    pop.addEventListener('mousedown', (e) => e.stopPropagation());  // no cerrar al usarlo
    pop.addEventListener('click', (e) => {
      const nav = e.target.closest('[data-nav]');
      if (nav) { return cambiarMes(parseInt(nav.dataset.nav, 10)); }
      const acc = e.target.closest('[data-accion]');
      if (acc) { return elegir(acc.dataset.accion === 'hoy' ? hoyISO() : ''); }
      const dia = e.target.closest('[data-iso]');
      if (dia) { elegir(dia.dataset.iso); }
    });
  }

  function cambiarMes(delta) {
    mes += delta;
    if (mes < 0) { mes = 11; anio--; }
    else if (mes > 11) { mes = 0; anio++; }
    pintar();
  }

  // ── Rejilla del mes (siempre 6 filas, lunes primero) ──
  function pintar() {
    pop.querySelector('.nm-cal-title').textContent = `${MESES[mes]} ${anio}`;
    const offset = (new Date(anio, mes, 1).getDay() + 6) % 7;   // 0 = lunes
    const inicio = new Date(anio, mes, 1 - offset);             // 1.ª celda de la rejilla
    const sel = (input && input.dataset.iso) || '';
    const hoy = hoyISO();

    let html = '';
    for (let i = 0; i < 42; i++) {
      const dia = new Date(inicio.getFullYear(), inicio.getMonth(), inicio.getDate() + i);
      const iso = aISO(dia.getFullYear(), dia.getMonth() + 1, dia.getDate());
      const cls = ['nm-cal-dia'];
      if (dia.getMonth() !== mes) cls.push('otro');
      if (iso === hoy) cls.push('hoy');
      if (iso === sel) cls.push('sel');
      html += `<button type="button" class="${cls.join(' ')}" data-iso="${iso}">${dia.getDate()}</button>`;
    }
    pop.querySelector('.nm-cal-grid').innerHTML = html;
  }

  function elegir(iso) {
    if (input) {
      input.dataset.iso = iso || '';
      input.value = fmt(iso);
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }
    cerrar();
  }

  // ── Abrir / cerrar ──
  function abrir(el) {
    if (!pop) crear();
    input = el;
    const base = (el.dataset.iso || hoyISO()).split('-');
    anio = parseInt(base[0], 10);
    mes = parseInt(base[1], 10) - 1;
    pintar();

    pop.hidden = false;
    pop.style.visibility = 'hidden';
    posicionar(el);
    pop.style.visibility = '';

    setTimeout(() => {   // no cerrar por el mismo click que abrió
      document.addEventListener('mousedown', cerrarAfuera);
      document.addEventListener('keydown', cerrarEsc);
      window.addEventListener('scroll', cerrar, true);
    }, 0);
  }

  function posicionar(el) {
    const r = el.getBoundingClientRect();
    const alto = pop.offsetHeight, ancho = pop.offsetWidth;
    let top = r.bottom + window.scrollY + 6;
    if (r.bottom + alto + 8 > window.innerHeight && r.top - alto - 6 > 0) {
      top = r.top + window.scrollY - alto - 6;               // no cabe abajo → arriba
    }
    let left = r.left + window.scrollX;
    left = Math.min(left, window.scrollX + window.innerWidth - ancho - 8);
    left = Math.max(left, window.scrollX + 8);
    pop.style.top = top + 'px';
    pop.style.left = left + 'px';
  }

  function cerrar() {
    if (pop) pop.hidden = true;
    input = null;
    document.removeEventListener('mousedown', cerrarAfuera);
    document.removeEventListener('keydown', cerrarEsc);
    window.removeEventListener('scroll', cerrar, true);
  }
  function cerrarAfuera(e) { if (pop && !pop.contains(e.target)) cerrar(); }
  function cerrarEsc(e) { if (e.key === 'Escape') cerrar(); }

  return { abrir, fmt };
})();
