// Simple "Flipkart-like" left tab switching
  const tabs = document.querySelectorAll('.payTab');
  const panels = document.querySelectorAll('.payPanel');

  function activateTab(targetId){
    panels.forEach(p => p.classList.add('hidden'));
    const panel = document.getElementById(targetId);
    if (panel) panel.classList.remove('hidden');

    tabs.forEach(t => t.classList.remove('bg-white'));
    const active = [...tabs].find(t => t.dataset.target === targetId);
    if (active) active.classList.add('bg-white');
  }

  tabs.forEach(btn => {
    btn.addEventListener('click', () => activateTab(btn.dataset.target));
  });

  // Default active
  activateTab('tabUPI');