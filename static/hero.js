(() => {
  const image = document.querySelector('#hero-image');
  const counter = document.querySelector('#hero-slide-number');
  const dots = document.querySelector('#hero-slider-dots');
  const slider = document.querySelector('#hero-product-slider');
  const art = document.querySelector('#hero-art');
  if (!image || !counter || !dots || !slider || !art) return;

  let products = [];
  let brand = 'Archives';
  let index = 0;

  function brandProducts(name) {
    return products.filter(product => product.brand === name && product.image);
  }

  function showSlide(nextIndex) {
    const items = brandProducts(brand);
    if (!items.length) return;
    index = (nextIndex + items.length) % items.length;
    const product = items[index];
    image.src = product.image;
    image.alt = `${product.brand} ${product.name}`;
    counter.textContent = `${String(index + 1).padStart(2, '0')} / ${String(items.length).padStart(2, '0')}`;
    document.querySelector('#hero-label').textContent = `IN THE VAULT / ${product.brand.toUpperCase()}`;
    document.querySelector('#hero-link-text').textContent = product.name;
    document.querySelector('#hero-feature').dataset.shopBrand = product.brand;
    dots.querySelectorAll('button').forEach((dot, dotIndex) => {
      dot.classList.toggle('active', dotIndex === index);
      dot.setAttribute('aria-current', String(dotIndex === index));
    });
  }

  function selectHeroBrand(name) {
    if (!brandProducts(name).length) return;
    brand = name;
    index = 0;
    dots.replaceChildren();
    brandProducts(name).forEach((product, dotIndex) => {
      const dot = document.createElement('button');
      dot.type = 'button';
      dot.className = 'hero-slider-dot';
      dot.setAttribute('aria-label', `${product.name}, ${dotIndex + 1}`);
      dot.addEventListener('click', () => showSlide(dotIndex));
      dots.append(dot);
    });
    showSlide(0);
  }

  document.querySelector('#hero-prev').addEventListener('click', () => showSlide(index - 1));
  document.querySelector('#hero-next').addEventListener('click', () => showSlide(index + 1));
  document.addEventListener('keydown', event => {
    if (!event.target.closest('#hero-product-slider, #hero-feature')) return;
    if (event.key === 'ArrowLeft') showSlide(index - 1);
    if (event.key === 'ArrowRight') showSlide(index + 1);
  });

  document.addEventListener('click', event => {
    const control = event.target.closest('[data-shop-brand], [data-brand]');
    if (!control) return;
    const requestedBrand = control.dataset.shopBrand || control.dataset.brand;
    const selectedBrand = requestedBrand === 'All' ? 'Archives' : requestedBrand;
    if (!brandProducts(selectedBrand).length) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    selectBrand(requestedBrand);
    selectHeroBrand(selectedBrand);
    document.querySelector('.hero').scrollIntoView({behavior: 'smooth', block: 'start'});
  }, true);

  document.addEventListener('DOMContentLoaded', () => {
    if (typeof updateBrandHero === 'function') updateBrandHero = () => {};
  }, {once: true});

  fetch('/api/products').then(response => {
    if (!response.ok) throw new Error('Unable to load products.');
    return response.json();
  }).then(data => {
    products = data;
    const imageName = decodeURIComponent(new URL(image.src).pathname.split('/').pop());
    art.classList.add('archives-slider');
    selectHeroBrand('Archives');
    const initialIndex = brandProducts('Archives').findIndex(product => product.image.endsWith(imageName));
    if (initialIndex >= 0) showSlide(initialIndex);
  }).catch(() => {});
})();
