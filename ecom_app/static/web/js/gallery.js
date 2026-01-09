(() => {
  const grid = document.getElementById('galleryGrid');
  const lb = document.getElementById('lightbox');
  const lbImg = document.getElementById('lbImg');
  const lbCaption = document.getElementById('lbCaption');
  const lbCount = document.getElementById('lbCount');

  const btnClose = document.getElementById('lbClose');
  const btnPrev = document.getElementById('lbPrev');
  const btnNext = document.getElementById('lbNext');
  const btnPlay = document.getElementById('lbPlay');
  const btnPause = document.getElementById('lbPause');

  if (!grid || !lb || !lbImg) return;

  const items = Array.from(grid.querySelectorAll('button[data-full]')).map(btn => ({
    full: btn.getAttribute('data-full'),
    caption: btn.getAttribute('data-caption') || '',
    alt: btn.querySelector('img')?.getAttribute('alt') || 'Gallery image'
  }));

  let index = 0;
  let autoplayTimer = null;

  function render(i) {
    index = (i + items.length) % items.length;
    const it = items[index];
    lbImg.src = it.full;
    lbImg.alt = it.alt;
    lbCaption.textContent = it.caption;
    lbCount.textContent = `${index + 1} / ${items.length}`;
  }

  function openAt(i) {
    render(i);
    lb.classList.remove('hidden');
    lb.classList.add('flex');
    document.documentElement.classList.add('overflow-hidden');
  }

  function close() {
    stopAutoplay();
    lb.classList.add('hidden');
    lb.classList.remove('flex');
    document.documentElement.classList.remove('overflow-hidden');
  }

  function prev() { render(index - 1); }
  function next() { render(index + 1); }

  function startAutoplay() {
    stopAutoplay();
    btnPlay.classList.add('hidden');
    btnPause.classList.remove('hidden');
    autoplayTimer = setInterval(next, 2500);
  }

  function stopAutoplay() {
    if (autoplayTimer) clearInterval(autoplayTimer);
    autoplayTimer = null;
    btnPause.classList.add('hidden');
    btnPlay.classList.remove('hidden');
  }

  // Click any image
  grid.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-full]');
    if (!btn) return;
    const i = items.findIndex(x => x.full === btn.getAttribute('data-full'));
    openAt(i >= 0 ? i : 0);
  });

  // Controls
  btnClose?.addEventListener('click', close);
  btnPrev?.addEventListener('click', prev);
  btnNext?.addEventListener('click', next);
  btnPlay?.addEventListener('click', startAutoplay);
  btnPause?.addEventListener('click', stopAutoplay);

  // Close on backdrop click
  lb.addEventListener('click', (e) => {
    if (e.target === lb) close();
  });

  // Keyboard
  window.addEventListener('keydown', (e) => {
    if (lb.classList.contains('hidden')) return;
    if (e.key === 'Escape') close();
    if (e.key === 'ArrowLeft') prev();
    if (e.key === 'ArrowRight') next();
  });

  // Swipe (mobile)
  let startX = null;
  lb.addEventListener('touchstart', (e) => {
    startX = e.touches[0]?.clientX ?? null;
  }, { passive: true });

  lb.addEventListener('touchend', (e) => {
    if (startX === null) return;
    const endX = e.changedTouches[0]?.clientX ?? startX;
    const dx = endX - startX;
    startX = null;
    if (Math.abs(dx) < 40) return;
    if (dx > 0) prev();
    else next();
  }, { passive: true });
})();
