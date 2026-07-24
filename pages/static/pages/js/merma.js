// Merma — carrito de pérdidas/deterioro
// item: { id, nombre, costo, stock, cantidad }
const mmCart = {};
let _mmActiveCat = '';

function mmFmt(val) {
  return '$' + Math.round(val).toLocaleString('es-CL');
}

// ── Filtros ───────────────────────────────────────────────────────────────────

function mmApplyFilters() {
  const term = (document.getElementById('mmSearch').value || '').toLowerCase().trim();
  document.querySelectorAll('.mm-card').forEach(card => {
    const matchTexto = card.dataset.nombre.toLowerCase().includes(term)
                    || (card.dataset.codigo || '').toLowerCase().includes(term);
    const matchCat = !_mmActiveCat || card.dataset.cat === _mmActiveCat;
    card.style.display = (matchTexto && matchCat) ? '' : 'none';
  });
}

// ── Carrito ───────────────────────────────────────────────────────────────────

// Regla: no se puede mermar lo que no hay en inventario (quedaría negativo).
// (El servidor lo revalida al confirmar: este stock puede estar viejo.)
function mmSinStock(nombre) {
  nmAviso(`"${nombre}" no tiene stock para dar de baja.`);
}
function mmTope(item) {
  nmAviso(`Solo quedan ${item.stock} unidades de "${item.nombre}".`);
}

function mmAddToCart(card) {
  const id = card.dataset.id;
  const stock = parseFloat(card.dataset.stock) || 0;
  const nombre = card.dataset.nombre;

  if (stock <= 0) { mmSinStock(nombre); return; }

  if (mmCart[id]) {
    if (mmCart[id].cantidad + 1 > mmCart[id].stock) { mmTope(mmCart[id]); return; }
    mmCart[id].cantidad += 1;
  } else {
    mmCart[id] = {
      id,
      nombre,
      costo:    parseFloat(card.dataset.costo) || 0,
      stock,
      cantidad: 1,
    };
  }
  mmRenderCart();
  card.classList.add('pc-card-added');
  setTimeout(() => card.classList.remove('pc-card-added'), 300);
}

function mmRemove(id) { delete mmCart[id]; mmRenderCart(); }

function mmAddQty(id, delta) {
  const item = mmCart[id];
  if (!item) return;
  const next = item.cantidad + delta;
  if (next < 1) { mmRemove(id); return; }
  if (next > item.stock) { mmTope(item); return; }
  item.cantidad = next;
  mmRenderCart();
}

function mmSetQty(id, val) {
  const item = mmCart[id];
  if (!item) return;
  let qty = parseInt(val);
  if (!qty || qty < 1) return;
  if (qty > item.stock) { qty = item.stock; mmTope(item); }   // se recorta al stock
  item.cantidad = qty;
  mmRenderCart();
}

// ── Render ────────────────────────────────────────────────────────────────────

function mmUpdateTotal() {
  const total = Object.values(mmCart).reduce((s, i) => s + i.costo * i.cantidad, 0);
  document.getElementById('mmTotal').textContent = mmFmt(total);
}

function mmRenderCart() {
  const container  = document.getElementById('mmCartItems');
  const confirmBtn = document.getElementById('mmConfirmarBtn');
  const items      = Object.values(mmCart);

  if (items.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon svg-icon icon-inventario xl icono-primario"></span>
        <p>Sin productos</p>
        <span class="empty-sub">Haz clic en un producto para agregarlo a la merma</span>
      </div>`;
    confirmBtn.disabled = true;
    mmUpdateTotal();
    return;
  }

  // Red de seguridad: si alguna línea supera el stock, no se puede confirmar.
  confirmBtn.disabled = items.some(i => i.cantidad > i.stock);

  container.innerHTML = items.map(item => {
    const sinStock = item.cantidad > item.stock;
    return `
    <div class="pc-cart-item" id="mmItem-${item.id}">
      <div class="pc-item-header">
        <span class="pc-item-name">${item.nombre}</span>
        <button class="pc-item-remove" onclick="mmRemove('${item.id}')" title="Quitar">✕</button>
      </div>
      <div class="pc-qty-row">
        <button class="pc-qty-btn" onclick="mmAddQty('${item.id}', -1)">−</button>
        <input type="number" id="mmQty-${item.id}"
               class="pc-ctrl-input pc-qty-input"
               value="${item.cantidad}" min="1" max="${item.stock}"
               onchange="mmSetQty('${item.id}', this.value)"
               oninput="mmSetQty('${item.id}', this.value)" />
        <button class="pc-qty-btn" onclick="mmAddQty('${item.id}', 1)">+</button>
        <span class="pc-subtotal">${mmFmt(item.costo * item.cantidad)}</span>
      </div>
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:.74rem;color:var(--gray);">
        <span>${mmFmt(item.costo)} costo c/u</span>
        ${sinStock ? `<span class="pv-stock-warn"><span class="svg-icon icon-alerta sm"></span> supera el stock (${item.stock})</span>` : ''}
      </div>
    </div>`;
  }).join('');

  mmUpdateTotal();
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  const search = document.getElementById('mmSearch');
  if (!search) return;  // no estamos en la vista de merma

  document.getElementById('mmClearCart').addEventListener('click', () => {
    Object.keys(mmCart).forEach(k => delete mmCart[k]);
    mmRenderCart();
  });

  document.getElementById('mmConfirmarBtn').addEventListener('click', () => {
    const items = Object.values(mmCart);
    if (!items.length) return;
    if (!confirm('¿Registrar esta merma? El stock se descontará.')) return;
    const payload = items.map(i => ({ id: i.id, cantidad: i.cantidad }));
    document.getElementById('mmCartData').value = JSON.stringify(payload);
    document.getElementById('mmForm').submit();
  });

  search.addEventListener('input', mmApplyFilters);

  search.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter') return;
    e.preventDefault();
    const term = search.value.toLowerCase().trim();
    if (!term) return;
    const cards = [...document.querySelectorAll('.mm-card')];
    let match = cards.find(c => (c.dataset.codigo || '').toLowerCase().split(/\s+/).includes(term));
    if (!match) {
      const visibles = cards.filter(c => c.style.display !== 'none');
      if (visibles.length === 1) match = visibles[0];
    }
    if (match) { mmAddToCart(match); search.value = ''; mmApplyFilters(); }
  });

  document.querySelectorAll('#mmCatFilter .chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('#mmCatFilter .chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      _mmActiveCat = chip.dataset.cat || '';
      mmApplyFilters();
    });
  });
});
