from django.db.models import Sum
from .models import Wishlist, CartItem


def wishlist_count(request):
    if request.user.is_authenticated:
        return {
            "wishlist_count": Wishlist.objects.filter(user=request.user).count()
        }
    return {"wishlist_count": 0}




def cart_count(request):
    # ---------- Logged-in user ----------
    if request.user.is_authenticated:
        total = (
            CartItem.objects
            .filter(cart__user=request.user)
            .aggregate(total=Sum("count"))["total"]
        )
        return {"cart_count": total or 0}

    # ---------- Guest user ----------
    cart = request.session.get("cart", {})
    total = sum(
        item.get("count", 0)
        for item in cart.values()
    )

    return {"cart_count": total}
