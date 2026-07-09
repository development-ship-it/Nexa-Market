// Punto de Venta — carrito de ventas
// item: { id, nombre, precio, precioMayor, cantMayor, stock, cantidad }
const pvCart = {};

let _pvActiveCat = '';

// ── Precio unitario: aplica mayorista si la cantidad alcanza el mínimo ────────

function pvPrecioUnitario(item) {
  if (item.precioMayor > 0 && item.cantMayor > 0 && item.cantidad >= item.cantMayor) {
    return item.precioMayor;
  }
  return item.precio;
}

function pvEsMayorista(item) {
  return item.precioMayor > 0 && item.cantMayor > 0 && item.cantidad >= item.cantMayor;
}

// ── Filtros ───────────────────────────────────────────────────────────────────

function pvApplyFilters() {
  const term = (document.getElementById('pvSearch').value || '').toLowerCase().trim();
  document.querySelectorAll('.pv-card').forEach(card => {
    const matchTexto = card.dataset.nombre.toLowerCase().includes(term)
                    || (card.dataset.codigo || '').toLowerCase().includes(term);
    const matchCat = !_pvActiveCat || card.dataset.cat === _pvActiveCat;
    card.style.display = (matchTexto && matchCat) ? '' : 'none';
  });
}

// ── Carrito ───────────────────────────────────────────────────────────────────

function pvAddToCart(card) {
  const id = card.dataset.id;
  if (pvCart[id]) {
    pvCart[id].cantidad += 1;
  } else {
    pvCart[id] = {
      id,
      nombre:      card.dataset.nombre,
      precio:      parseFloat(card.dataset.precio) || 0,
      precioMayor: parseFloat(card.dataset.precioMayor) || 0,
      cantMayor:   parseFloat(card.dataset.cantMayor) || 0,
      stock:       parseFloat(card.dataset.stock) || 0,
      cantidad:    1,
    };
  }
  pvRenderCart();
  card.classList.add('pc-card-added');
  setTimeout(() => card.classList.remove('pc-card-added'), 300);
}

function pvRemove(id) {
  delete pvCart[id];
  pvRenderCart();
}

function pvAddQty(id, delta) {
  if (!pvCart[id]) return;
  const next = pvCart[id].cantidad + delta;
  if (next < 1) { pvRemove(id); return; }
  pvCart[id].cantidad = next;
  pvRenderCart();
}

function pvSetQty(id, val) {
  const qty = parseInt(val);
  if (!qty || qty < 1) return;
  pvCart[id].cantidad = qty;
  pvRenderCart();
}

// ── Render ────────────────────────────────────────────────────────────────────

function pvFmt(val) {
  return '$' + Math.round(val).toLocaleString('es-CL');
}

function pvUpdateTotal() {
  const total = Object.values(pvCart).reduce((s, i) => s + pvPrecioUnitario(i) * i.cantidad, 0);
  document.getElementById('pvTotal').textContent = pvFmt(total);
}

function pvRenderCart() {
  const container  = document.getElementById('pvCartItems');
  const confirmBtn = document.getElementById('pvConfirmarBtn');
  const items      = Object.values(pvCart);

  if (items.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon">🛒</span>
        <p>Carrito vacío</p>
        <span class="empty-sub">Haz clic en un producto para agregarlo</span>
      </div>`;
    confirmBtn.disabled = true;
    pvUpdateTotal();
    return;
  }

  confirmBtn.disabled = false;

  container.innerHTML = items.map(item => {
    const precioU  = pvPrecioUnitario(item);
    const esMayor  = pvEsMayorista(item);
    const sinStock = item.cantidad > item.stock;
    return `
    <div class="pc-cart-item" id="pvItem-${item.id}">
      <div class="pc-item-header">
        <span class="pc-item-name">${item.nombre}</span>
        <button class="pc-item-remove" onclick="pvRemove('${item.id}')" title="Quitar">✕</button>
      </div>

      <div class="pc-qty-row">
        <button class="pc-qty-btn" onclick="pvAddQty('${item.id}', -1)">−</button>
        <input type="number" id="pvQty-${item.id}"
               class="pc-ctrl-input pc-qty-input"
               value="${item.cantidad}" min="1"
               onchange="pvSetQty('${item.id}', this.value)"
               oninput="pvSetQty('${item.id}', this.value)" />
        <button class="pc-qty-btn" onclick="pvAddQty('${item.id}', 1)">+</button>
        <span class="pc-subtotal">${pvFmt(precioU * item.cantidad)}</span>
      </div>

      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:.74rem;color:var(--gray);">
        <span>${pvFmt(precioU)} c/u</span>
        ${esMayor ? '<span class="pv-precio-mayor-badge">Precio mayorista</span>' : ''}
        ${item.cantMayor > 0 && !esMayor ? `<span>· mayorista desde ${item.cantMayor}u</span>` : ''}
        ${sinStock ? `<span class="pv-stock-warn">⚠ supera el stock (${item.stock})</span>` : ''}
      </div>
    </div>`;
  }).join('');

  pvUpdateTotal();
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  const search = document.getElementById('pvSearch');
  if (!search) return;  // no estamos en el punto de venta

  // Limpiar carrito
  document.getElementById('pvClearCart').addEventListener('click', () => {
    Object.keys(pvCart).forEach(k => delete pvCart[k]);
    pvRenderCart();
  });

  // Confirmar venta → POST (el servidor recalcula precios desde la BD)
  document.getElementById('pvConfirmarBtn').addEventListener('click', () => {
    const items = Object.values(pvCart);
    if (!items.length) return;
    const payload = items.map(i => ({ id: i.id, cantidad: i.cantidad }));
    document.getElementById('pvCartData').value = JSON.stringify(payload);
    document.getElementById('pvForm').submit();
  });

  // Búsqueda por nombre o código
  search.addEventListener('input', pvApplyFilters);

  // Escáner: Enter agrega el producto cuyo código coincide (o el único visible)
  search.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter') return;
    e.preventDefault();
    const term = search.value.toLowerCase().trim();
    if (!term) return;
    const cards = [...document.querySelectorAll('.pv-card')];
    let match = cards.find(c => (c.dataset.codigo || '').toLowerCase().split(/\s+/).includes(term));
    if (!match) {
      const visibles = cards.filter(c => c.style.display !== 'none');
      if (visibles.length === 1) match = visibles[0];
    }
    if (match) {
      pvAddToCart(match);
      search.value = '';
      pvApplyFilters();
    }
  });

  // Filtro de categorías
  document.querySelectorAll('#pvCatFilter .chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('#pvCatFilter .chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      _pvActiveCat = chip.dataset.cat || '';
      pvApplyFilters();
    });
  });
});
