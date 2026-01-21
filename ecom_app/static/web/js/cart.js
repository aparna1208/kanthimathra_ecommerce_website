document.addEventListener("DOMContentLoaded", function () {

    console.log("cart.js loaded");

    // ==========================
    // ADD TO CART (redirect)
    // ==========================
    if (window.ADD_TO_CART_URL && window.CART_PAGE_URL) {

        document.body.addEventListener("click", function (e) {

            const btn = e.target.closest(".add-to-cart-btn");
            if (!btn) return;

            e.preventDefault();

            const productId = btn.dataset.product;
            const quantity = btn.dataset.quantity || "default";
            const count = btn.dataset.count || 1;

            if (!productId) return;

            fetch(window.ADD_TO_CART_URL, {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCookie("csrftoken"),
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                body: `product_id=${productId}&quantity=${quantity}&count=${count}`
            })
            .then(res => res.json())
            .then(data => {
                if (!data.success) return;

                updateCartCount(data.cart_count);
                window.location.href = window.CART_PAGE_URL;
            });
        });
    }

    // ==========================
    // SHIPPING CHANGE
    // ==========================
    document.querySelectorAll('input[name="ship"]').forEach(radio => {
        radio.addEventListener("change", recalculateSummary);
    });

    // Initial calculation
    recalculateSummary();
});


// ==========================
// CART ACTIONS (+ / − / remove)
// ==========================

document.addEventListener("click", function (e) {

    if (e.target.closest(".qty-plus")) {
        updateQty(e.target.closest(".cart-row"), 1);
    }

    if (e.target.closest(".qty-minus")) {
        updateQty(e.target.closest(".cart-row"), -1);
    }

    if (e.target.closest(".remove-btn")) {
        removeItem(e.target.closest(".cart-row"));
    }
});


function updateQty(row, delta) {
    const qtyEl = row.querySelector(".qty-val");
    let count = parseInt(qtyEl.textContent) + delta;
    if (count < 0) count = 0;

    const productId = row.dataset.id;
    const quantity = row.querySelector(".qty-plus").dataset.quantity;

    fetch(window.UPDATE_CART_URL, {
        method: "POST",
        headers: {
            "X-CSRFToken": getCookie("csrftoken"),
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: `product_id=${productId}&quantity=${quantity}&count=${count}`
    })
    .then(res => res.json())
    .then(data => {
        if (!data.success) return;

        if (count === 0) {
            row.remove();
        } else {
            qtyEl.textContent = count;

            const price = parseFloat(row.dataset.price) || 0;

            // ✅ ROUND ROW TOTAL
            row.querySelector(".row-total").textContent =
                Math.round(price * count);
        }

        updateCartCount(data.cart_count);
        recalculateSummary();
    });
}


function removeItem(row) {
    const productId = row.dataset.id;
    const quantity = row.querySelector(".remove-btn").dataset.quantity;

    fetch(window.REMOVE_CART_URL, {
        method: "POST",
        headers: {
            "X-CSRFToken": getCookie("csrftoken"),
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: `product_id=${productId}&quantity=${quantity}`
    })
    .then(res => res.json())
    .then(data => {
        if (!data.success) return;

        row.remove();
        updateCartCount(data.cart_count);
        recalculateSummary();
    });
}


// ==========================
// ORDER SUMMARY (LIVE UPDATE)
// ==========================

function recalculateSummary() {
    let subtotal = 0;
    let discount = 0;
    let mrp = 0;

    document.querySelectorAll(".cart-row").forEach(row => {
        const qty = parseInt(row.querySelector(".qty-val")?.textContent) || 0;
        const price = parseFloat(row.dataset.price) || 0;
        const original = parseFloat(row.dataset.originalPrice) || 0;

        subtotal += price * qty;
        mrp += original * qty;
        discount += (original - price) * qty;
    });

    const shipping = parseFloat(
        document.querySelector('input[name="ship"]:checked')?.value || 0
    );

    const grandTotal = mrp - discount + shipping;

    // ✅ UPDATE DOM (ROUNDED)
    const mrpEl = document.getElementById("mrpTotal");
    const discountEl = document.getElementById("discount");
    const grandTotalEl = document.getElementById("grandTotal");

    if (mrpEl) mrpEl.textContent = Math.round(mrp);
    if (discountEl) discountEl.textContent = Math.round(discount);
    if (grandTotalEl) grandTotalEl.textContent = Math.round(grandTotal);
}


// ==========================
// CART COUNT
// ==========================

function updateCartCount(count) {
    const cartCountEl = document.getElementById("cart-count");
    if (cartCountEl) {
        cartCountEl.textContent = count;
    }
}


// ==========================
// CSRF HELPER
// ==========================

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        document.cookie.split(";").forEach(cookie => {
            cookie = cookie.trim();
            if (cookie.startsWith(name + "=")) {
                cookieValue = decodeURIComponent(
                    cookie.substring(name.length + 1)
                );
            }
        });
    }
    return cookieValue;
}
