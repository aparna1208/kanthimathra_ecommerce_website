document.addEventListener("DOMContentLoaded", function () {

    document.addEventListener("click", function (e) {
        const clickedBtn = e.target.closest(".wishlist-btn");
        if (!clickedBtn) return;

        const productId = clickedBtn.dataset.product;
        const isAuth = clickedBtn.dataset.auth === "true";
        const toggleUrl = clickedBtn.dataset.url;
        const loginUrl = clickedBtn.dataset.login;

        // Not logged in
        if (!isAuth) {
            if (confirm("Please login to add this product to wishlist")) {
                const nextUrl = window.location.pathname + window.location.search;
                window.location.href = loginUrl + "?next=" + nextUrl;
            }
            return;
        }

        fetch(toggleUrl, {
            method: "POST",
            headers: {
                "X-CSRFToken": getCookie("csrftoken"),
                "Content-Type": "application/x-www-form-urlencoded"
            },
            body: "product_id=" + productId
        })
        .then(res => res.json())
        .then(data => {

            // 🔥 Update ALL heart buttons for same product
            const allButtons = document.querySelectorAll(
                `.wishlist-btn[data-product="${productId}"]`
            );

            allButtons.forEach(btn => {
                const icon = btn.querySelector("svg");
                if (!icon) return;

                if (data.added) {
                    // ❤️ Filled heart
                    icon.classList.remove("text-zinc-400", "fill-white");
                    icon.classList.add("text-brownMain", "fill-brownMain");
                } else {
                    // 🤍 Empty white heart
                    icon.classList.remove("text-brownMain", "fill-brownMain");
                    icon.classList.add("text-zinc-400", "fill-white");
                }
            });

            // Header wishlist count
            const count = document.getElementById("wishlist-count");
            if (count) {
                count.innerText = data.count;
            }
        })
        .catch(error => console.error("Wishlist Error:", error));
    });

});

// CSRF helper
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name + "=")) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
