// ---------- Address modal logic ----------
const modal = document.getElementById('addrModal');
const overlay = document.getElementById('addrOverlay');
const closeBtn = document.getElementById('addrClose');
const form = document.getElementById('addrForm');

const inputTitle = document.getElementById('addrTitle');
const inputAddr = document.getElementById('addrText');
const inputPhone = document.getElementById('addrPhone');
const inputDef = document.getElementById('addrDefault');

function openModal(payload) {
    inputTitle.value = payload.title || '';
    inputAddr.value = payload.address || '';
    inputPhone.value = payload.phone || '';
    inputDef.checked = String(payload.default) === 'true';

    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    modal.classList.add('hidden');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
}

document.querySelectorAll('[data-edit-address]').forEach(btn => {
    btn.addEventListener('click', () => {
        openModal({
            title: btn.getAttribute('data-title'),
            address: btn.getAttribute('data-address'),
            phone: btn.getAttribute('data-phone'),
            default: btn.getAttribute('data-default')
        });
    });
});

closeBtn.addEventListener('click', closeModal);
overlay.addEventListener('click', closeModal);

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !modal.classList.contains('hidden')) closeModal();
});

form.addEventListener('submit', (e) => {
    e.preventDefault();

    // Hook your backend/save logic here
    // Example: send data via fetch()

    closeModal();
});




const accMenuBtn = document.getElementById('accMenuBtn');
const accSidebar = document.getElementById('accSidebar');

accMenuBtn?.addEventListener('click', () => {
    accSidebar?.classList.toggle('hidden');
});