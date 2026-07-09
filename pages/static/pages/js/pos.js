// Point of Sale JS

const cart = [];

document.addEventListener('DOMContentLoaded', () => {
  initPosSearch();
  initCart();
});

function initPosSearch() {
  const input = document.getElementById('posSearch');
  if (!input) return;
  input.addEventListener('input', () => {
    const term = input.value.toLowerCase();
    document.querySelectorAll('.pos-card').forEach(card => {
      const name = card.querySelector('.pos-name')?.textContent.toLowerCase() || '';
      card.style.display = name.includes(term) ? '' : 'none';
    });
  });
}

function initCart() {
  const clearBtn = document.getElementById('clearCart');
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      cart.length = 0;
      renderCart();
    });
  }
}

function addToCart(id, name, price) {
  const existing = cart.find(i => i.id === id);
  if (existing) {
    existing.qty += 1;
  } else {
    cart.push({ id, name, price: parseFloat(price), qty: 1 });
  }
  renderCart();
}

function renderCart() {
  const container = document.getElementById('cartItems');
  const totalEl = document.getElementById('cartTotal');
  const checkoutBtn = document.getElementById('checkoutBtn');
  if (!container) return;

  if (cart.length === 0) {
    container.innerHTML = `<div class="empty-state"><span class="empty-icon">🛒</span><p>Carrito vacío</p></div>`;
    if (totalEl) totalEl.textContent = '$0';
    if (checkoutBtn) checkoutBtn.disabled = true;
    return;
  }

  const total = cart.reduce((s, i) => s + i.price * i.qty, 0);
  container.innerHTML = cart.map(item => `
    <div class="cart-item" data-id="${item.id}">
      <div class="cart-item-info">
        <span class="cart-item-name">${item.name}</span>
        <span class="cart-item-price">${formatCLP(item.price)}</span>
      </div>
      <div class="cart-item-qty">
        <button onclick="changeQty('${item.id}', -1)">−</button>
        <span>${item.qty}</span>
        <button onclick="changeQty('${item.id}', 1)">+</button>
      </div>
    </div>
  `).join('');

  if (totalEl) totalEl.textContent = formatCLP(total);
  if (checkoutBtn) checkoutBtn.disabled = false;
}

function changeQty(id, delta) {
  const item = cart.find(i => i.id === id);
  if (!item) return;
  item.qty += delta;
  if (item.qty <= 0) cart.splice(cart.indexOf(item), 1);
  renderCart();
}
