const filterBtn = document.getElementById('filterBtn');
const filterDrawer = document.getElementById('filterDrawer');
const filterOverlay = document.getElementById('filterOverlay');
const filterClose = document.getElementById('filterClose');

function openFilters() {
  filterDrawer.classList.remove('-translate-x-full');
  filterDrawer.classList.add('translate-x-0');
  filterOverlay.classList.remove('opacity-0', 'pointer-events-none');
  filterOverlay.classList.add('opacity-100');
  document.body.style.overflow = 'hidden';
}

function closeFilters() {
  filterDrawer.classList.add('-translate-x-full');
  filterDrawer.classList.remove('translate-x-0');
  filterOverlay.classList.add('opacity-0', 'pointer-events-none');
  filterOverlay.classList.remove('opacity-100');
  document.body.style.overflow = '';
}

filterBtn?.addEventListener('click', openFilters);
filterClose?.addEventListener('click', closeFilters);
filterOverlay?.addEventListener('click', closeFilters);
