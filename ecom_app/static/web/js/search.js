const mSearchToggle = document.getElementById("mSearchToggle");
  const mSearchBar = document.getElementById("mSearchBar");
  const mSearchInput = document.getElementById("mSearchInput");
  const mSearchClear = document.getElementById("mSearchClear");

  function openMobileSearch() {
    mSearchBar.classList.remove("max-h-0", "opacity-0");
    mSearchBar.classList.add("max-h-24", "opacity-100");
    mSearchToggle.setAttribute("aria-expanded", "true");
    requestAnimationFrame(() => mSearchInput?.focus());
  }

  function closeMobileSearch() {
    mSearchBar.classList.add("max-h-0", "opacity-0");
    mSearchBar.classList.remove("max-h-24", "opacity-100");
    mSearchToggle.setAttribute("aria-expanded", "false");
    mSearchInput.value = "";
  }

  mSearchToggle?.addEventListener("click", () => {
    const isOpen = mSearchToggle.getAttribute("aria-expanded") === "true";
    isOpen ? closeMobileSearch() : openMobileSearch();
  });

  mSearchClear?.addEventListener("click", () => {
    mSearchInput.value = "";
    mSearchInput.focus();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeMobileSearch();
  });