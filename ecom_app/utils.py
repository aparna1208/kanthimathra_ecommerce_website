from decimal import Decimal
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from .models import Product, Cart, CartItem

from io import BytesIO
from django.core.mail import EmailMessage
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.conf import settings

# ========================
# EMAIL
# ========================
def send_otp_email(email, otp):
    send_mail(
        subject="Verify your email - Kanthi Mantra",
        message=f"Your OTP is {otp}. It is valid for 2 minutes.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )


# ========================
# SESSION CART (GUEST USERS)
# ========================

def get_cart(request):
    return request.session.get("cart", {})


def _cart_key(product_id, quantity_variant):
    """
    Creates a unique key for product + variant
    """
    return f"{product_id}|{quantity_variant}"


def add_to_cart(request, product_id, quantity_variant, count=1):
    """
    Add item to session cart (guest user)
    """
    if count <= 0:
        return

    cart = request.session.get("cart", {})
    key = _cart_key(product_id, quantity_variant)

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return

    if key in cart:
        cart[key]["count"] += count
    else:
        cart[key] = {
            "product_id": product.id,
            "name": product.product_name,
            "quantity": quantity_variant,
            "count": count,

            # ✅ ROUNDED VALUES FOR UI
            "price": str(product.offer_price_rounded),
            "original_price": str(product.original_price_rounded),
            "discount_percent": product.discount_percentage,

            "image": product.thumbnail.url if product.thumbnail else "",
        }

    request.session["cart"] = cart
    request.session.modified = True


def update_cart(request, product_id, quantity_variant, count):
    """
    Update item count in session cart
    """
    cart = request.session.get("cart", {})
    key = _cart_key(product_id, quantity_variant)

    if key not in cart:
        return

    if count <= 0:
        del cart[key]
    else:
        cart[key]["count"] = count

    request.session["cart"] = cart
    request.session.modified = True


def remove_from_cart(request, product_id, quantity_variant):
    """
    Remove item from session cart
    """
    cart = request.session.get("cart", {})
    key = _cart_key(product_id, quantity_variant)

    cart.pop(key, None)

    request.session["cart"] = cart
    request.session.modified = True


def cart_totals(request):
    """
    Calculate totals for session cart
    """
    cart = request.session.get("cart", {})

    subtotal = sum(
        Decimal(item["price"]) * item["count"]
        for item in cart.values()
    )

    total_items = sum(item["count"] for item in cart.values())

    return {
        "subtotal": subtotal,
        "total_items": total_items,
    }


# ========================
# DB CART (LOGGED-IN USERS)
# ========================

def get_or_create_cart(user):
    return Cart.objects.get_or_create(user=user)[0]


def add_to_db_cart(user, product_id, quantity_variant, count=1):
    """
    Add item to database cart (logged-in user)
    """
    if count <= 0:
        return

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return

    cart = get_or_create_cart(user)

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        quantity=quantity_variant,
        defaults={
            "count": count,
            "price": product.offer_price_rounded,   # ✅ CHANGE
            "thumbnail": product.thumbnail,
        },
    )

    if not created:
        cart_item.count += count
        cart_item.save()


# ========================
# MERGE SESSION CART → DB CART (ON LOGIN)
# ========================

@transaction.atomic
def merge_session_cart_to_db(request):
    """
    Merge guest cart into user cart after login
    """
    if not request.user.is_authenticated:
        return

    session_cart = request.session.get("cart", {})
    if not session_cart:
        return

    cart = get_or_create_cart(request.user)

    for item in session_cart.values():
        try:
            product = Product.objects.get(id=item["product_id"])
        except Product.DoesNotExist:
            continue

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            quantity=item["quantity"],
            defaults={
                "count": item["count"],
                "price": Decimal(item["price"]),
                "thumbnail": product.thumbnail,
            },
        )

        if not created:
            cart_item.count += item["count"]
            cart_item.save()

    # clear session cart
    del request.session["cart"]
    request.session.modified = True







def send_invoice_email(order):
    """
    Sends ONLY the A4 invoice PDF (no HTML UI) to registered email
    """

    template = get_template("web/invoice_pdf.html")
    html = template.render({
        "order": order,
        "items": order.items.all(),
    })

    pdf_buffer = BytesIO()
    pisa.CreatePDF(html, dest=pdf_buffer, encoding="UTF-8")
    pdf_buffer.seek(0)

    email = EmailMessage(
        subject=f"Invoice for Order {order.order_id}",
        body="Please find your invoice attached.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.user.email],
    )

    email.attach(
        f"Invoice_{order.order_id}.pdf",
        pdf_buffer.read(),
        "application/pdf"
    )

    email.send(fail_silently=False)