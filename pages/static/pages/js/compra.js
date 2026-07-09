// Punto de Compra — carrito de compras

// item: { id, nombre, precio, precioVenta, cantidad, fechaVencimiento }
const pcCart = {};

let _activeCat  = '';
let _activeProv = '';

// ── Filtros combinados ────────────────────────────────────────────────────────

function pcApplyFilters() {
  const term = (document.getElementById('pcSearch').value || '').toLowerCase();
  document.querySelectorAll('.pc-card').forEach(card => {
    const matchNombre = card.dataset.nombre.toLowerCase().includes(term);
    const matchCat    = !_activeCat  || card.dataset.cat  === _activeCat;
    const matchProv   = !_activeProv || card.dataset.prov === _activeProv;
    card.style.display = (matchNombre && matchCat && matchProv) ? '' : 'none';
  });
}

// ── Agregar al carrito ────────────────────────────────────────────────────────

function pcAddToCart(card) {
  const id          = card.dataset.id;
  const nombre      = card.dataset.nombre;
  const precio      = parseFloat(card.dataset.precio) || 0;
  const precioVenta = parseFloat(card.dataset.venta)  || 0;

  if (pcCart[id]) {
    pcCart[id].cantidad += 1;
    // Solo actualizar cantidad y subtotal sin re-renderizar todo
    const input = document.getElementById(`pcQty-${id}`);
    if (input) input.value = pcCart[id].cantidad;
    _refreshSubtotal(id);
    pcUpdateTotal();
  } else {
    pcCart[id] = { id, nombre, precio, precioVenta, cantidad: 1, fechaVencimiento: '' };
    pcRenderCart();
  }

  card.classList.add('pc-card-added');
  setTimeout(() => card.classList.remove('pc-card-added'), 300);
}

// ── Eliminar ──────────────────────────────────────────────────────────────────

function pcRemove(id) {
  delete pcCart[id];
  pcRenderCart();
}

// ── Cantidad con +/- ──────────────────────────────────────────────────────────

function pcAddQty(id, delta) {
  if (!pcCart[id]) return;
  const next = pcCart[id].cantidad + delta;
  if (next < 1) { pcRemove(id); return; }
  pcCart[id].cantidad = next;
  const input = document.getElementById(`pcQty-${id}`);
  if (input) input.value = next;
  _refreshSubtotal(id);
  pcUpdateTotal();
}

function pcSetQty(id, val) {
  const qty = parseInt(val);
  if (!qty || qty < 1) { pcRemove(id); return; }
  pcCart[id].cantidad = qty;
  _refreshSubtotal(id);
  pcUpdateTotal();
}

// ── Precios ───────────────────────────────────────────────────────────────────

function _round10(val) {
  return Math.round(val / 10) * 10;
}

function pcSetCompra(id, val) {
  const p = parseFloat(val);
  if (isNaN(p) || p < 0) return;
  pcCart[id].precio = p;
  _refreshSubtotal(id);
  pcUpdateTotal();
}

function pcSetVenta(id, val) {
  const p = parseFloat(val);
  if (isNaN(p) || p < 0) return;
  pcCart[id].precioVenta = p;
}

function pcRoundInput(inputEl, id, field) {
  const v = parseFloat(inputEl.value);
  if (isNaN(v) || v < 0) return;
  const rounded = _round10(v);
  inputEl.value = rounded;
  if (field === 'compra') {
    pcCart[id].precio = rounded;
    _refreshSubtotal(id);
    pcUpdateTotal();
  } else {
    pcCart[id].precioVenta = rounded;
  }
}

// ── Fecha de vencimiento ──────────────────────────────────────────────────────

function pcSetFecha(id, val) {
  if (pcCart[id]) pcCart[id].fechaVencimiento = val;
}

// ── Guardar precios en BD (AJAX) ──────────────────────────────────────────────

function pcSavePrecios(id) {
  const item = pcCart[id];
  if (!item) return;

  const url = PC_API_BASE + id + '/precios/';
  const btn = document.getElementById(`pcSaveBtn-${id}`);
  if (btn) { btn.textContent = '⏳'; btn.disabled = true; }

  const pcRounded = _round10(item.precio);
  const pvRounded = _round10(item.precioVenta);

  fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': PC_CSRF,
    },
    body: JSON.stringify({
      precio_compra: pcRounded,
      precio_venta:  pvRounded,
    }),
  })
  .then(r => r.json())
  .then(data => {
    if (btn) {
      btn.disabled = false;
      if (data.ok) {
        btn.textContent = '✓';
        btn.style.color = 'var(--green)';
        // Actualizar cart con valores redondeados devueltos por el servidor
        pcCart[id].precio      = data.precio_compra;
        pcCart[id].precioVenta = data.precio_venta;
        _refreshSubtotal(id);
        pcUpdateTotal();
        // Reflejar en la tarjeta del grid para futuros adds
        const card = document.querySelector(`.pc-card[data-id="${id}"]`);
        if (card) {
          card.dataset.precio = data.precio_compra;
          card.dataset.venta  = data.precio_venta;
          const priceEl = card.querySelector('.pos-price');
          if (priceEl) priceEl.textContent = pcFmt(data.precio_compra);
        }
      } else {
        btn.textContent = '✗';
        btn.style.color = 'var(--red)';
      }
      setTimeout(() => {
        if (btn) { btn.textContent = '💾'; btn.style.color = ''; btn.disabled = false; }
      }, 2000);
    }
  })
  .catch(() => {
    if (btn) {
      btn.disabled = false;
      btn.textContent = '✗';
      btn.style.color = 'var(--red)';
      setTimeout(() => { btn.textContent = '💾'; btn.style.color = ''; }, 2000);
    }
  });
}

// ── Subtotal y total ──────────────────────────────────────────────────────────

function _refreshSubtotal(id) {
  const el = document.getElementById(`pcSub-${id}`);
  if (el && pcCart[id]) {
    el.textContent = pcFmt(pcCart[id].precio * pcCart[id].cantidad);
  }
}

function pcUpdateTotal() {
  const total = Object.values(pcCart).reduce((s, i) => s + i.precio * i.cantidad, 0);
  document.getElementById('pcTotal').textContent = pcFmt(total);
}

function pcFmt(val) {
  return '$' + Math.round(val).toLocaleString('es-CL');
}

// ── Renderizar carrito completo ───────────────────────────────────────────────

function pcRenderCart() {
  const container  = document.getElementById('pcCartItems');
  const confirmBtn = document.getElementById('pcConfirmarBtn');
  const items      = Object.values(pcCart);

  if (items.length === 0) {
    container.innerHTML = `
      <div id="pcEmptyCart" class="empty-state">
        <span class="empty-icon">📥</span>
        <p>Carrito vacío</p>
        <span class="empty-sub">Haz clic en un producto para agregarlo</span>
      </div>`;
    confirmBtn.disabled = true;
    pcUpdateTotal();
    return;
  }

  confirmBtn.disabled = false;

  container.innerHTML = items.map(item => `
    <div class="pc-cart-item" id="pcItem-${item.id}">

      <!-- Nombre + quitar -->
      <div class="pc-item-header">
        <span class="pc-item-name">${item.nombre}</span>
        <button class="pc-item-remove" onclick="pcRemove('${item.id}')" title="Quitar">✕</button>
      </div>

      <!-- Cantidad -->
      <div class="pc-qty-row">
        <button class="pc-qty-btn" onclick="pcAddQty('${item.id}', -1)">−</button>
        <input type="number" id="pcQty-${item.id}"
               class="pc-ctrl-input pc-qty-input"
               value="${item.cantidad}" min="1"
               onchange="pcSetQty('${item.id}', this.value)"
               oninput="pcSetQty('${item.id}', this.value)" />
        <button class="pc-qty-btn" onclick="pcAddQty('${item.id}', 1)">+</button>
        <span class="pc-subtotal" id="pcSub-${item.id}">${pcFmt(item.precio * item.cantidad)}</span>
      </div>

      <!-- Precios compra / venta + guardar -->
      <div class="pc-price-row">
        <span class="pc-row-icon" title="Precios">$</span>
        <div class="pc-price-fields">
          <div class="pc-price-field">
            <span class="pc-field-lbl">Compra</span>
            <input type="number" class="pc-ctrl-input pc-price-input"
                   value="${item.precio}" min="0" step="10"
                   oninput="pcSetCompra('${item.id}', this.value)"
                   onblur="pcRoundInput(this, '${item.id}', 'compra')" />
          </div>
          <span class="pc-arrow">→</span>
          <div class="pc-price-field">
            <span class="pc-field-lbl">Venta</span>
            <input type="number" class="pc-ctrl-input"
                   value="${item.precioVenta}" min="0" step="10"
                   oninput="pcSetVenta('${item.id}', this.value)"
                   onblur="pcRoundInput(this, '${item.id}', 'venta')" />
          </div>
          <button class="pc-save-btn" id="pcSaveBtn-${item.id}"
                  onclick="pcSavePrecios('${item.id}')"
                  title="Guardar precios en el artículo">💾</button>
        </div>
      </div>

      <!-- Fecha de vencimiento -->
      <div class="pc-date-row">
        <span class="pc-row-icon" title="Vencimiento">📅</span>
        <input type="date" class="pc-ctrl-input pc-date-input"
               value="${item.fechaVencimiento}"
               onchange="pcSetFecha('${item.id}', this.value)" />
        <span class="pc-field-lbl" style="margin-left:4px;">Vencimiento</span>
      </div>

    </div>
  `).join('');

  pcUpdateTotal();
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {

  // Limpiar carrito
  document.getElementById('pcClearCart').addEventListener('click', () => {
    Object.keys(pcCart).forEach(k => delete pcCart[k]);
    pcRenderCart();
  });

  // Confirmar compra → POST
  document.getElementById('pcConfirmarBtn').addEventListener('click', () => {
    const items = Object.values(pcCart);
    if (!items.length) return;

    const payload = items.map(i => ({
      id:                i.id,
      nombre:            i.nombre,
      cantidad:          i.cantidad,
      precio:            i.precio,
      precio_venta:      i.precioVenta,
      fecha_vencimiento: i.fechaVencimiento || null,
    }));

    document.getElementById('pcCartData').value = JSON.stringify(payload);
    document.getElementById('pcForm').submit();
  });

  // Búsqueda
  document.getElementById('pcSearch').addEventListener('input', pcApplyFilters);

  // Filtro categoría
  document.querySelectorAll('#catFilter .chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('#catFilter .chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      _activeCat = chip.dataset.cat || '';
      pcApplyFilters();
    });
  });

  // Quitar chips de categoría duplicados
  const seenCat = new Set();
  document.querySelectorAll('#catFilter .chip[data-cat]').forEach(chip => {
    const val = chip.dataset.cat;
    if (!val) return;
    if (seenCat.has(val)) { chip.remove(); } else { seenCat.add(val); }
  });

  // Filtro proveedor
  document.querySelectorAll('#provFilter .chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('#provFilter .chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      _activeProv = chip.dataset.prov || '';
      pcApplyFilters();
    });
  });
});
