const accountMessage = document.querySelector('#account-message');

async function sendAccountRequest(path, payload) {
  const response = await fetch(path, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Account request failed.');
  return result;
}

async function loadCustomerAccount() {
  const response = await fetch('/api/auth/me');
  const result = await response.json();
  const user = result.user;
  if (!user) {
    document.querySelector('#auth-panel').hidden = false;
    document.querySelector('#customer-orders').hidden = true;
    document.querySelector('#account-logout').hidden = true;
    accountMessage.textContent = 'Sign in or create an account to view your orders.';
    return;
  }
  if (user.role !== 'customer') {
    accountMessage.textContent = 'This is a customer account page. Open the seller portal for seller accounts.';
    document.querySelector('#auth-panel').hidden = true;
    document.querySelector('#customer-orders').hidden = true;
    document.querySelector('#account-logout').hidden = false;
    return;
  }
  document.querySelector('#auth-panel').hidden = true;
  document.querySelector('#customer-orders').hidden = false;
  document.querySelector('#account-logout').hidden = false;
  document.querySelector('#customer-heading').textContent = `Orders for ${user.display_name}`;
  accountMessage.textContent = `Signed in as ${user.email}`;
  const ordersResponse = await fetch('/api/orders');
  const orders = await ordersResponse.json();
  if (!ordersResponse.ok) throw new Error(orders.error || 'Could not load your orders.');
  const list = document.querySelector('#customer-order-list');
  list.replaceChildren();
  if (!orders.length) {
    list.textContent = 'No orders yet.';
    return;
  }
  for (const item of orders) {
    const card = document.createElement('article');
    card.className = 'portal-card';
    const heading = document.createElement('h3');
    heading.textContent = `Order #${item.order_id} · ${item.name}`;
    const details = document.createElement('p');
    details.textContent = `${item.shop_name} · ${item.size} × ${item.quantity} · ${item.status} · ${item.priority} priority`;
    const date = document.createElement('p');
    date.className = 'muted';
    date.textContent = new Date(item.created_at).toLocaleString();
    card.append(heading, details, date);
    list.append(card);
  }
}

for (const [formId, endpoint] of [
  ['customer-login', '/api/auth/login'],
  ['customer-register', '/api/auth/register']
]) {
  document.querySelector(`#${formId}`).addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form));
    try {
      await sendAccountRequest(endpoint, payload);
      form.reset();
      await loadCustomerAccount();
    } catch (error) {
      accountMessage.textContent = error.message;
    }
  });
}

document.querySelector('#account-logout').addEventListener('click', async () => {
  await sendAccountRequest('/api/auth/logout', {});
  await loadCustomerAccount();
});

loadCustomerAccount().catch(error => { accountMessage.textContent = error.message; });
