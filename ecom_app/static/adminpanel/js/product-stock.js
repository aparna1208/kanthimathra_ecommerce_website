// static/adminpanel/js/product-stock.js

document.addEventListener("DOMContentLoaded", function () {
    const stockSelect = document.getElementById("stock_status");
    const quantityGroup = document.getElementById("quantity_group");
    const quantityInput = document.getElementById("quantity_input");

    if (!stockSelect || !quantityGroup || !quantityInput) {
        return; // Exit if elements not found (safety)
    }

    function toggleQuantityField() {
        const status = stockSelect.value;

        if (status === "In Stock") {
            quantityGroup.style.display = "flex";   // or "block" if needed
            quantityInput.disabled = false;
            quantityInput.required = true;
        } else {
            // Out Of Stock
            quantityGroup.style.display = "none";
            quantityInput.disabled = true;
            quantityInput.required = false;
            quantityInput.value = 0;  // Auto-set to 0
        }
    }

    // Run on page load (important for Edit page where value is pre-selected)
    toggleQuantityField();

    // Run when user changes selection
    stockSelect.addEventListener("change", toggleQuantityField);

    // If using Select2, also listen to its change event
    if (window.jQuery && stockSelect.classList.contains("js-example-basic-single")) {
        jQuery(stockSelect).on("select2:select", toggleQuantityField);
    }
});