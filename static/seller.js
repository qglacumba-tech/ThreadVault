const sellerMessage = document.querySelector('#seller-message');
const productForm = document.querySelector('#product-form');

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...(options.body ? {'Content-Type': 'application/json'} : {}),
      ...(options.headers || {})
    }
  });
  const result = response.status === 204 ? {} : await response.json();
  if (!response.ok) throw new Error(result.error || 'Request failed.');
  return result;
}

function stockRowsToText(rows) {
  return rows.map(row => `${row.size}:${row.quantity}`).join('\n');
}

function parseStock(text) {
  return text.split(/\r?\n/).map(line => {
    const separator = line.lastIndexOf(':');
    if (separator < 1) throw new Error('Use one size:quantity entry per line, for example S:5.');
    const size = line.slice(0, separator).trim();
    const quantityText = line.slice(separator + 1).trim();
    if (!/^\d+$/.test(quantityText)) throw new Error(`Stock for ${size} must be a whole number.`);
    return {size, quantity: Number(quantityText)};
  });
}

function clearProductForm() {
  productForm.reset();
  productForm.elements.product_id.value = '';
  productForm.hidden = true;
}

async function loadProducts() {
  const products = await api('/api/seller/products');
  const list = document.querySelector('#seller-products');
  list.replaceChildren();
  if (!products.length) {
    list.textContent = 'No products yet. Add a listing to make it available in the customer shop.';
    return;
  }
  for (const product of products) {
    const card = document.createElement('article');
    card.className = 'portal-card';
    const heading = document.createElement('h3');
    heading.textContent = product.name;
    const details = document.createElement('p');
    details.textContent = `${product.category} · PHP ${Number(product.price).toFixed(2)} · ${product.stock.map(row => `${row.size}: ${row.quantity}`).join(', ')}`;
    const description = document.createElement('p');
    description.className = 'muted';
    description.textContent = product.description;
    const actions = document.createElement('div');
    actions.className = 'portal-actions';
    const edit = document.createElement('button');
    edit.textContent = 'EDIT';
    edit.onclick = () => {
      productForm.elements.product_id.value = product.id;
      productForm.elements.name.value = product.name;
      productForm.elements.category.value = product.category;
      productForm.elements.description.value = product.description;
      productForm.elements.price.value = product.price;
      productForm.elements.image_url.value = product.image_url || '';
      productForm.elements.stock.value = stockRowsToText(product.stock);
      productForm.hidden = false;
      productForm.scrollIntoView({behavior: 'smooth', block: 'center'});
    };
    const remove = document.createElement('button');
    remove.textContent = 'REMOVE';
    remove.onclick = async () => {
      if (!confirm(`Remove ${product.name} from the customer shop?`)) return;
      try {
        await api(`/api/seller/products/${product.id}`, {method: 'DELETE'});
        await refreshSellerWorkspace();
      } catch (error) {
        sellerMessage.textContent = error.message;
      }
    };
    actions.append(edit, remove);
    card.append(heading, details, description, actions);
    list.append(card);
  }
}

async function loadOrders() {
  const orders = await api('/api/seller/orders');
  const list = document.querySelector('#seller-orders');
  const completedList = document.querySelector('#seller-completed-orders');
  list.replaceChildren();
  completedList.replaceChildren();
  const openOrders = orders.filter(order => order.status !== 'fulfilled');
  const completedOrders = orders.filter(order => order.status === 'fulfilled');
  if (!openOrders.length) {
    list.textContent = 'There are no open orders for your shop.';
  }
  if (!completedOrders.length) {
    completedList.textContent = 'No fulfilled order items yet.';
  }
  for (const order of openOrders) {
    const card = document.createElement('article');
    card.className = 'portal-card';
    const heading = document.createElement('h3');
    heading.textContent = `Order #${order.order_id} · ${order.name}`;
    const details = document.createElement('p');
    details.textContent = `${order.customer_name} · ${order.size} × ${order.quantity} · ${order.priority} · ${order.status}`;
    const update = document.createElement('button');
    update.className = 'primary';
    update.textContent = order.status === 'pending' ? 'START PROCESSING' : 'MARK FULFILLED';
    update.onclick = async () => {
      const status = order.status === 'pending' ? 'processing' : 'fulfilled';
      try {
        await api(`/api/seller/order-items/${order.item_id}`, {
          method: 'PATCH',
          body: JSON.stringify({status})
        });
        await refreshSellerWorkspace();
      } catch (error) {
        sellerMessage.textContent = error.message;
      }
    };
    card.append(heading, details, update);
    list.append(card);
  }
  for (const order of completedOrders) {
    const card = document.createElement('article');
    card.className = 'portal-card';
    const heading = document.createElement('h3');
    heading.textContent = `Order #${order.order_id} · ${order.name}`;
    const details = document.createElement('p');
    details.textContent = `${order.customer_name} · ${order.size} × ${order.quantity} · ${order.priority} · fulfilled`;
    card.append(heading, details);
    completedList.append(card);
  }
}

async function refreshSellerWorkspace() {
  await Promise.all([loadProducts(), loadOrders()]);
}

async function loadSellerAccount() {
  const result = await api('/api/auth/me');
  const user = result.user;
  if (!user) {
    document.querySelector('#seller-auth').hidden = false;
    document.querySelector('#seller-workspace').hidden = true;
    document.querySelector('#seller-logout').hidden = true;
    sellerMessage.textContent = 'Sign in or open a seller account to manage your shop.';
    return;
  }
  if (user.role !== 'seller') {
    sellerMessage.textContent = 'This account is not a seller account. Sign out and use seller sign-in.';
    document.querySelector('#seller-auth').hidden = true;
    document.querySelector('#seller-workspace').hidden = true;
    document.querySelector('#seller-logout').hidden = false;
    return;
  }
  document.querySelector('#seller-auth').hidden = true;
  document.querySelector('#seller-workspace').hidden = false;
  document.querySelector('#seller-logout').hidden = false;
  document.querySelector('#seller-title').textContent = user.shop_name;
  sellerMessage.textContent = `Signed in as ${user.display_name} · ${user.email}`;
  await refreshSellerWorkspace();
}

for (const [formId, endpoint] of [
  ['seller-login', '/api/auth/login'],
  ['seller-register', '/api/auth/register']
]) {
  document.querySelector(`#${formId}`).addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget;
    try {
      await api(endpoint, {
        method: 'POST',
        body: JSON.stringify(Object.fromEntries(new FormData(form)))
      });
      form.reset();
      await loadSellerAccount();
    } catch (error) {
      sellerMessage.textContent = error.message;
    }
  });
}

document.querySelector('#new-product').addEventListener('click', () => {
  clearProductForm();
  productForm.hidden = false;
  productForm.scrollIntoView({behavior: 'smooth', block: 'center'});
});

document.querySelector('#cancel-product').addEventListener('click', clearProductForm);

productForm.elements.image_file.addEventListener('change', async event => {
  const image = event.currentTarget.files[0];
  if (!image) return;
  const formData = new FormData();
  formData.append('image', image);
  try {
    const response = await fetch('/api/seller/upload', {method: 'POST', body: formData});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Image upload failed.');
    productForm.elements.image_url.value = result.image_url;
    sellerMessage.textContent = 'Image uploaded. Save the product to keep the image with its listing.';
  } catch (error) {
    sellerMessage.textContent = error.message;
  }
});

productForm.addEventListener('submit', async event => {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    const payload = Object.fromEntries(new FormData(form));
    const productId = payload.product_id;
    delete payload.product_id;
    delete payload.image_file;
    payload.stock = parseStock(payload.stock);
    await api(productId ? `/api/seller/products/${productId}` : '/api/seller/products', {
      method: productId ? 'PUT' : 'POST',
      body: JSON.stringify(payload)
    });
    clearProductForm();
    sellerMessage.textContent = 'Product saved.';
    await refreshSellerWorkspace();
  } catch (error) {
    sellerMessage.textContent = error.message;
  }
});

document.querySelector('#undo-status').addEventListener('click', async () => {
  try {
    await api('/api/seller/orders/undo-last-status', {method: 'POST'});
    sellerMessage.textContent = 'The most recent order status change was undone.';
    await loadOrders();
  } catch (error) {
    sellerMessage.textContent = error.message;
  }
});

document.querySelector('#seller-logout').addEventListener('click', async () => {
  try {
    await api('/api/auth/logout', {method: 'POST'});
    await loadSellerAccount();
  } catch (error) {
    sellerMessage.textContent = error.message;
  }
});

loadSellerAccount().catch(error => { sellerMessage.textContent = error.message; });
