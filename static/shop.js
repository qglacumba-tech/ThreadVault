const $ = selector => document.querySelector(selector);
let products = [], category = 'All', brand = 'All', cart = [];
const money = amount => new Intl.NumberFormat('en-PH', {style: 'currency', currency: 'PHP'}).format(amount);
const hasPrice = product => Number.isFinite(product.price) && product.price >= 0;
const canPurchase = product => hasPrice(product) && product.sizes.length > 0;
const priceLabel = product => hasPrice(product) ? money(product.price) : 'Price to be announced';

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function picture(product) {
  const box = element('div', 'product-image');
  const placeholder = element('div', 'placeholder');
  placeholder.append(element('b', '', String(product.id).padStart(2, '0')), document.createTextNode('PHOTO COMING SOON'));
  box.append(placeholder);
  if (product.image) {
    const img = new Image();
    img.alt = `${product.brand} — ${product.name}`;
    img.decoding = 'async';
    img.onload = () => { placeholder.remove(); box.prepend(img); };
    img.src = product.image;
  }
  return box;
}

function save() {
  try { localStorage.setItem('your-brand-cart', JSON.stringify(cart)); } catch {}
  $('#bag-count').textContent = cart.reduce((count, item) => count + item.quantity, 0);
}

function brandProducts() {
  return products.filter(product => brand === 'All' || product.brand === brand);
}

function renderCategories() {
  const categories = ['All', ...new Set(brandProducts().map(product => product.category))];
  if (!categories.includes(category)) category = 'All';
  $('#categories').replaceChildren();
  categories.forEach(value => {
    const button = element('button', '', value);
    button.dataset.category = value;
    button.setAttribute('aria-pressed', String(value === category));
    button.onclick = () => {
      category = value;
      document.querySelectorAll('[data-category]').forEach(option => {
        option.setAttribute('aria-pressed', String(option.dataset.category === category));
      });
      render();
    };
    $('#categories').append(button);
  });
}
function updateBrandHero(selectedBrand) {

  const heroArt = document.querySelector('#hero-art');
  const heroImage = document.querySelector('#hero-image');
  const heroLabel = document.querySelector('#hero-label');
  const heroLinkText = document.querySelector('#hero-link-text');
  const heroFeature = document.querySelector('#hero-feature');

  if (!heroArt || !heroImage) return;


  /* Fade image before changing */
  heroArt.classList.add('brand-changing');


  setTimeout(() => {

    if (selectedBrand === 'Archives') {

      heroImage.src = '/assets/ArchivesBG.jpg';

      heroImage.alt = 'Archives';

      heroArt.classList.add('archives-hero');

      if (heroLabel) {
        heroLabel.textContent = 'IN THE VAULT / ARCHIVES';
      }

      if (heroLinkText) {
        heroLinkText.textContent = 'Shop Archives';
      }

      if (heroFeature) {
        heroFeature.dataset.shopBrand = 'Archives';
      }

    } else {

      /* Default ThreadVault hero */

      heroImage.src = '/assets/IMG_5480.PNG';

      heroImage.alt = 'Archives Game Over graphic tee';

      heroArt.classList.remove('archives-hero');

      if (heroLabel) {
        heroLabel.textContent = 'IN THE VAULT / ARCHIVES';
      }

      if (heroLinkText) {
        heroLinkText.textContent = 'Explore the collection';
      }

      if (heroFeature) {
        heroFeature.dataset.shopBrand = 'Archives';
      }

    }


    heroImage.onload = () => {
      heroArt.classList.remove('brand-changing');
    };


    /* fallback in case image was cached */
    if (heroImage.complete) {
      heroArt.classList.remove('brand-changing');
    }

  }, 250);

}
function selectBrand(value) {

  brand = value;
  category = 'All';

  $('#search').value = '';

  document.querySelectorAll('[data-brand]').forEach(button => {
    button.setAttribute(
      'aria-pressed',
      String(button.dataset.brand === brand)
    );
  });

  updateBrandHero(value);

  renderCategories();
  render();
}

function render() {
  const query = $('#search').value.trim().toLowerCase();
  const collection = brandProducts();
  const list = collection.filter(product =>
    (category === 'All' || product.category === category) &&
    `${product.brand} ${product.name} ${product.category}`.toLowerCase().includes(query)
  );
  const sort = $('#sort').value;
  if (sort !== 'featured') {
    list.sort((a, b) => {
      // Unpriced pieces follow priced products in either sort direction.
      if (!hasPrice(a) || !hasPrice(b)) return Number(hasPrice(b)) - Number(hasPrice(a));
      return sort === 'low' ? a.price - b.price : b.price - a.price;
    });
  }
  $('#collection-title').textContent = brand === 'All' ? 'ALL PRODUCTS' : brand.toUpperCase();
  $('#product-count').textContent = `${list.length} ${list.length === 1 ? 'piece' : 'pieces'}`;
  const grid = $('#products');
  grid.replaceChildren();
  list.forEach(product => {
    const card = element('button', 'product-card');
    card.setAttribute('aria-label', `View ${product.brand} ${product.name}`);
    const img = picture(product);
    img.append(element('span', 'quick', 'QUICK VIEW'));
    card.append(img, element('p', 'product-brand', product.brand), element('h3', '', product.name), element('p', 'price', priceLabel(product)));
    card.onclick = () => details(product);
    grid.append(card);
  });
  if (!list.length) {
    const empty = element('div', 'empty-state');
    const comingSoon = brand !== 'All' && collection.length === 0;
    empty.append(
      element('p', 'eyebrow', comingSoon ? brand.toUpperCase() : 'THE COLLECTION'),
      element('h3', '', comingSoon ? 'COLLECTION COMING SOON.' : 'NO MATCHING PIECES.'),
      element('p', 'muted', comingSoon ? `New pieces from ${brand} will appear here. Explore the Archives collection while you wait.` : 'Try another search or browse the full collection.')
    );
    const reset = element('button', 'primary', comingSoon ? 'EXPLORE ARCHIVES' : 'VIEW ALL PRODUCTS');
    reset.onclick = () => selectBrand(comingSoon ? 'Archives' : 'All');
    empty.append(reset);
    grid.append(empty);
  }
}

function details(product) {
  const content = $('#product-details');
  content.replaceChildren();
  const row = element('div', 'detail-layout'), info = element('div');
  const title = element('h2', '', product.name);
  title.id = 'detail-title';
  info.append(element('p', 'product-brand', `${product.brand} / ${product.category}`), title, element('p', 'detail-price', priceLabel(product)), element('p', 'muted', product.description));
  if (canPurchase(product)) {
    const label = element('label', '', 'Size');
    label.htmlFor = 'size';
    const sizes = element('select');
    sizes.id = 'size';
    product.sizes.forEach(size => {
      const option = element('option', '', size);
      option.value = size;
      sizes.append(option);
    });
    const add = element('button', 'primary', 'ADD TO BAG');
    add.onclick = () => {
      const existing = cart.find(item => item.id === product.id && item.size === sizes.value);
      if (existing) {
        if (existing.quantity >= 10) { notice('Maximum 10 of each item.'); return; }
        existing.quantity++;
      } else cart.push({id: product.id, size: sizes.value, quantity: 1});
      save();
      $('#product-dialog').close();
      notice('Added to your bag.');
    };
    info.append(label, sizes, add);
  } else {
    const availability = element('div', 'availability');
    availability.append(element('strong', '', 'IN THE VAULT'), element('p', 'muted', 'Pricing and available sizes will be announced.'));
    const pending = element('button', 'primary', 'DETAILS COMING SOON');
    pending.disabled = true;
    availability.append(pending);
    info.append(availability);
  }
  row.append(picture(product), info);
  content.append(row);
  $('#product-dialog').showModal();
}

let timer;
function notice(text) {
  $('#toast').textContent = text;
  $('#toast').style.display = 'block';
  clearTimeout(timer);
  timer = setTimeout(() => $('#toast').style.display = 'none', 2400);
}

function subtotal() {
  return cart.reduce((total, item) => total + products.find(product => product.id === item.id).price * item.quantity, 0);
}

function renderCart() {
  const items = $('#cart-items');
  items.replaceChildren();
  $('#cart-bottom').replaceChildren();
  if (!cart.length) {
    items.append(element('p', 'muted', 'Your bag is empty. Find something you love in the collection.'));
    return;
  }
  cart.forEach((item, index) => {
    const product = products.find(product => product.id === item.id), row = element('div', 'cart-row'), info = element('div');
    info.append(element('p', 'product-brand', product.brand), element('h3', '', product.name), element('p', 'muted', `Size: ${item.size} · ${money(product.price)} each`));
    const qty = element('div', 'qty');
    for (const [text, delta] of [['−', -1], ['+', 1]]) {
      const button = element('button', '', text);
      button.setAttribute('aria-label', `${delta < 0 ? 'Decrease' : 'Increase'} quantity of ${product.name}, ${item.size}`);
      button.disabled = delta > 0 && item.quantity >= 10;
      button.onclick = () => { item.quantity += delta; if (item.quantity === 0) cart.splice(index, 1); save(); renderCart(); };
      qty.append(button);
      if (delta < 0) qty.append(element('span', '', item.quantity));
    }
    const remove = element('button', 'remove', 'Remove');
    remove.onclick = () => { cart.splice(index, 1); save(); renderCart(); };
    qty.append(remove);
    info.append(qty);
    row.append(info, element('span', 'price', money(product.price * item.quantity)));
    items.append(row);
  });
  const total = element('div', 'total');
  total.append(element('span', '', 'Subtotal'), element('strong', '', money(subtotal())));
  const checkout = element('button', 'primary', 'CHECK OUT');
  checkout.onclick = () => {
    $('#cart-dialog').close();
    $('#checkout-summary').replaceChildren();
    cart.forEach(item => {
      const product = products.find(product => product.id === item.id);
      $('#checkout-summary').append(element('p', '', `${product.brand} ${product.name} / ${item.size} × ${item.quantity} — ${money(product.price * item.quantity)}`));
    });
    $('#checkout-summary').append(element('strong', '', `Subtotal: ${money(subtotal())}`));
    $('#checkout-status').textContent = '';
    $('#finish-demo').disabled = false;
    $('#checkout-dialog').showModal();
  };
  $('#cart-bottom').append(total, element('p', 'muted', 'Order records are saved. Payment is not configured.'), checkout);
}

$('#finish-demo').onclick = async () => {
  const button = $('#finish-demo');
  button.disabled = true;
  $('#checkout-status').textContent = 'Submitting your order…';
  try {
    const response = await fetch('/api/orders', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        priority: $('#order-priority').value,
        items: cart.map(item => ({product_id: item.id, size: item.size, quantity: item.quantity}))
      })
    });
    const result = await response.json();
    if (!response.ok) {
      if (response.status === 401) {
        $('#checkout-status').textContent = 'Sign in as a customer to place an order.';
      button.disabled = false;
      return;
    }
      throw new Error(result.error || 'Unable to place order.');
    }
    cart = [];
    save();
    $('#checkout-status').textContent = `Order #${result.order_id} was placed. No payment was collected.`;
    notice(`Order #${result.order_id} placed.`);
    setTimeout(() => $('#checkout-dialog').close(), 1300);
  } catch (error) {
    $('#checkout-status').textContent = error.message;
    button.disabled = false;
  }
};
$('#open-cart').onclick = () => { renderCart(); $('#cart-dialog').showModal(); };
document.querySelectorAll('[data-close]').forEach(button => button.onclick = () => document.getElementById(button.dataset.close).close());
document.querySelectorAll('[data-brand]').forEach(button => button.onclick = () => selectBrand(button.dataset.brand));
document.querySelectorAll('[data-shop-brand]').forEach(link => link.onclick = () => selectBrand(link.dataset.shopBrand));
$('#sort').onchange = render;
$('#search').oninput = render;

fetch('/api/products').then(response => {
  if (!response.ok) throw Error('Unable to load the catalog');
  return response.json();
}).then(data => {
  products = data;
  try {
    const saved = JSON.parse(localStorage.getItem('your-brand-cart') || '[]');
    if (Array.isArray(saved)) cart = saved.filter(item => item && Number.isInteger(item.quantity) && item.quantity > 0 && item.quantity <= 10 && products.some(product => product.id === item.id && canPurchase(product) && product.sizes.includes(item.size)));
  } catch {}
  document.querySelectorAll('[data-brand-status]').forEach(status => {
    const count = products.filter(product => product.brand === status.dataset.brandStatus).length;
    status.textContent = count ? `${count} pieces / Explore collection` : 'Collection coming soon';
    status.closest('.brand-card').classList.toggle('has-products', count > 0);
  });
  save();
  renderCategories();
  render();
}).catch(() => { $('#products').textContent = 'Unable to load products. Restart app.py, then refresh this page.'; });
