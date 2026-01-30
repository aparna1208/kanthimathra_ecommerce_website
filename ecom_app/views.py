from decimal import Decimal, ROUND_HALF_UP
from urllib import request
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from .utils import send_otp_email
from django.contrib.auth import get_user_model 
from django.contrib.auth import logout
import random
from django.views.decorators.http import require_POST,require_http_methods
from .utils import add_to_cart, cart_totals, merge_session_cart_to_db, add_to_db_cart, update_cart, remove_from_cart

import razorpay
from django.core.mail import send_mail
from reportlab.pdfgen import canvas
from django.http import HttpResponse
import uuid
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.core.paginator import Paginator
from .utils import send_invoice_email
from django.db import transaction
from django.db.models import Count,Sum

from .models import *

import re
from urllib.parse import urlparse, parse_qs,quote
from django.urls import reverse
import os


User = get_user_model()


#------------------------------------------------#
#-------------WEB FRONTEND VIEWS-----------------#
#------------------------------------------------#



def index(request):
    categories = Category.objects.all()
    products = Product.objects.all()[:8]
    home_video = HomeVideo.objects.first()
    sliders = HomeSlider.objects.all().order_by("-id")
    center_banner = HomeCenterBanner.objects.first()
    end_banners = HomeEndBanner.objects.all().order_by("-id") 
    flash_news = HomeFlashNews.objects.all().order_by("-id")[:10]

    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = Wishlist.objects.filter(
            user=request.user
        ).values_list("product_id", flat=True)

    context = {
        'categories': categories,
        'products': products,
        'wishlist_ids': wishlist_ids,
        'sliders': sliders, 
        'center_banner': center_banner,
        "home_video": home_video,
        "end_banners": end_banners,
        "flash_news": flash_news,

    }

    return render(request, 'web/index.html', context)


@login_required(login_url='web:login')
def account(request):
    orders = (
        Order.objects
        .filter(user=request.user)
        .prefetch_related("items", "items__product")
        .order_by("-created_at")
    )

    context = {
        "orders": orders
    }
    return render(request, "web/account.html", context)


def address(request):
    return render(request, 'web/address.html')


def account_settings(request):
    return render(request, 'web/settings.html')

def order_history(request):
    return render(request, 'web/orders.html')


def blog(request):
    return render(request, 'web/blog.html')


def blog_single(request):
    return render(request, 'web/blog_single.html')


def contact(request):
    contact = ContactPage.objects.first()  
    return render(request, "web/contact.html", {"contact": contact})


def about(request):
    return render(request, 'web/about.html')



def category(request):
    categories = (
        Category.objects
        .annotate(product_count=Count("products"))  
        .order_by("-created_at")
    )
    return render(request, "web/category.html", {"categories": categories})




def category_single(request, cat_id):
    category = get_object_or_404(Category, id=cat_id)

    #  Filter products under this category
    product_list = Product.objects.filter(category=category).order_by("-created_at")

    #  Pagination (8 products per page)
    paginator = Paginator(product_list, 4)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "category": category,

        #  Use page_obj instead of products
        "page_obj": page_obj,
        "products": page_obj,   # optional: so your old template loop still works

        "total_products": product_list.count(),
    }
    return render(request, "web/category_single.html", context)

def register_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if not email or not password or not confirm_password:
            messages.error(request, "All fields are required")
            return redirect("web:register")

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("web:register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("web:register")

        # Cleanup old OTPs
        EmailOTP.objects.filter(email=email, purpose="register").delete()
        PendingRegistration.objects.filter(email=email).delete()

        # Create OTP
        otp_obj = EmailOTP.objects.create(
            email=email,
            purpose="register"
        )

        PendingRegistration.objects.create(
            email=email,
            password_hash=make_password(password),
            otp=otp_obj
        )

        send_otp_email(email, otp_obj.otp)

        request.session["pending_email"] = email
        messages.success(request, "OTP sent to your email")
        return redirect("web:verify_otp")

    return render(request, "web/register.html")

def verify_otp_view(request):
    email = request.session.get("pending_email")

    if not email:
        messages.error(request, "Session expired")
        return redirect("web:register")

    try:
        pending = PendingRegistration.objects.get(email=email)
        otp_obj = pending.otp
    except PendingRegistration.DoesNotExist:
        messages.error(request, "Invalid request")
        return redirect("web:register")

    if request.method == "POST":
        entered_otp = request.POST.get("otp")

        if otp_obj.is_expired():
            messages.error(request, "OTP expired")
            return redirect("web:register")

        if entered_otp != otp_obj.otp:
            otp_obj.attempts += 1
            otp_obj.save()
            messages.error(request, "Invalid OTP")
            return redirect("web:verify_otp")

        otp_obj.mark_verified()
        pending.is_verified = True
        pending.save()

        user = User.objects.create(
            username=email,
            email=email,
            password=pending.password_hash
        )

        Account.objects.create(user=user, is_email_verified=True)

        pending.delete()
        otp_obj.delete()
        request.session.pop("pending_email", None)

        messages.success(request, "Registration successful")
        return redirect("web:login")

    return render(request, "web/otp.html", {"email": email})


#-----14_01_2026---- done by rdev-------------------------------
@require_POST
def resend_otp_view(request):
    email = (
        request.session.get("pending_email") or
        request.session.get("reset_email")
    )

    if not email:
        return JsonResponse({"status": "session_expired"}, status=400)

    try:
        otp_obj = EmailOTP.objects.filter(
            email=email,
            is_verified=False
        ).latest("created_at")
    except EmailOTP.DoesNotExist:
        return JsonResponse({"status": "invalid"}, status=400)

    # 🔁 regenerate OTP
    otp_obj.otp = str(random.randint(100000, 999999))
    otp_obj.expires_at = timezone.now() + timezone.timedelta(minutes=5)
    otp_obj.attempts = 0
    otp_obj.save()

    send_otp_email(email, otp_obj.otp)

    return JsonResponse({"status": "success"})


def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "Email not registered")
            return redirect("web:forgot_password")

        # Cleanup old reset OTPs
        EmailOTP.objects.filter(email=email, purpose="reset").delete()

        otp_obj = EmailOTP.objects.create(
            email=email,
            user=user,
            purpose="reset"
        )

        send_otp_email(email, otp_obj.otp)

        #  THESE TWO LINES ARE MANDATORY
        request.session["reset_email"] = email
        request.session.modified = True

        messages.success(request, "OTP sent to your email")
        return redirect("web:verify_reset_otp")

    return render(request, "web/forgot_password.html")



def verify_reset_otp_view(request):
    email = request.session.get("reset_email")

    if not email:
        messages.error(request, "Session expired")
        return redirect("web:forgot_password")

    try:
        otp_obj = EmailOTP.objects.get(
            email=email,
            purpose="reset",
            is_verified=False
        )
    except EmailOTP.DoesNotExist:
        messages.error(request, "OTP not found")
        return redirect("web:forgot_password")

    if request.method == "POST":
        entered_otp = request.POST.get("otp")

        if otp_obj.is_expired():
            messages.error(request, "OTP expired. Please resend OTP.")
            return render(request, "web/otp.html", {
                "email": email,
                "otp_expired": True
            })

        if entered_otp != otp_obj.otp:
            otp_obj.attempts += 1
            otp_obj.save()
            messages.error(request, "Invalid OTP")
            return redirect("web:verify_reset_otp")

        #  OTP VERIFIED SUCCESSFULLY
        otp_obj.mark_verified()

        # SET SESSION FLAG
        request.session["reset_verified"] = True
        request.session.modified = True

        #  REDIRECT TO RESET PASSWORD PAGE
        return redirect("web:reset_password")

    return render(request, "web/otp.html", {"email": email})



def reset_password_view(request):
    #  Block direct access
    if not request.session.get("reset_verified"):
        return redirect("web:forgot_password")

    email = request.session.get("reset_email")
    if not email:
        return redirect("web:forgot_password")

    user = User.objects.get(email=email)

    if request.method == "POST":
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("web:reset_password")

        user.set_password(password)
        user.save()

        # 🧹 Cleanup
        EmailOTP.objects.filter(email=email, purpose="reset").delete()
        request.session.flush()

        messages.success(request, "Password reset successful. Please login.")
        return redirect("web:account")

    return render(request, "web/reset_password.html")


def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        if not email or not password:
            messages.error(request, "Email and password are required")
            return redirect("web:login")

        user = authenticate(request, username=email, password=password)

        if user is not None:
            if not hasattr(user, "account") or not user.account.is_email_verified:
                messages.error(request, "Please verify your email first")
                return redirect("web:login")

            # ✅ LOGIN USER
            login(request, user)

            # ✅ MERGE SESSION CART → DB CART
            merge_session_cart_to_db(request)

            # ✅ SAFE REDIRECT (GET or POST)
            next_url = request.POST.get("next") or request.GET.get("next")
            return redirect(next_url if next_url else "web:index")

        messages.error(request, "Invalid email or password")

    return render(request, "web/login.html")

def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully")
    return redirect("web:login")


def shop(request):
    categories = Category.objects.all()
    products = Product.objects.all()

    # ---------------- FILTERS ----------------
    selected_categories = request.GET.getlist('category')
    if selected_categories:
        products = products.filter(category__id__in=selected_categories)

    availability = request.GET.getlist('availability')
    if availability:
        products = products.filter(stock__in=availability)

    min_price = request.GET.get('min_price')
    if min_price:
        products = products.filter(offer_price__gte=min_price)

    max_price = request.GET.get('max_price')
    if max_price:
        products = products.filter(offer_price__lte=max_price)

    # ---------------- SORTING ----------------
    sort_by = request.GET.get('sort')

    if sort_by == 'az':
        products = products.order_by('product_name')

    elif sort_by == 'price_low':
        products = products.order_by('offer_price')

    elif sort_by == 'price_high':
        products = products.order_by('-offer_price')

    else:
        # default → Best selling
        products = products.order_by('-id')

    # ---------------- COUNT ----------------
    # total_products = products.count()

    # ---------------- WISHLIST ----------------
    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = Wishlist.objects.filter(
            user=request.user
        ).values_list('product_id', flat=True)
    
       # -------- PAGINATION --------
    paginator = Paginator(products, 6)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'categories': categories,
        'products': page_obj,         
        'page_obj': page_obj,
        'total_products': paginator.count,
        'wishlist_ids': wishlist_ids,
        'selected_categories': list(map(int, selected_categories)),
        'availability': availability,
        'min_price': min_price,
        'max_price': max_price,
        'sort_by': sort_by,
    }

    return render(request, 'web/shop.html', context)


def account_redirect(request):
    if request.user.is_authenticated:
        return redirect('web:account')
    else:
        return redirect('web:login')


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)

    related_products = Product.objects.filter(
        category=product.category
    ).exclude(id=product.id)[:4]

    wishlist_ids = []

    if request.user.is_authenticated:
        wishlist_ids = Wishlist.objects.filter(
            user=request.user
        ).values_list("product_id", flat=True)

    context = {
        'product': product,
        'related_products': related_products,
        'wishlist_ids': wishlist_ids,
    }
    return render(request, 'web/product_detail.html', context)


@login_required
def toggle_wishlist(request):
    product_id = request.POST.get("product_id")
    product = get_object_or_404(Product, id=product_id)

    wishlist, created = Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )

    if not created:
        wishlist.delete()
        added = False
    else:
        added = True

    count = Wishlist.objects.filter(user=request.user).count()

    return JsonResponse({
        "added": added,
        "count": count
    })



@login_required
def wishlist(request):
    wishlist_items = Wishlist.objects.filter(
        user=request.user
    ).select_related("product")

    context = {
        "wishlist_items": wishlist_items
    }
    return render(request, "web/wishlist.html", context)


def add_to_cart_view(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request"})

    product_id = request.POST.get("product_id")
    quantity_variant = request.POST.get("quantity")
    count = int(request.POST.get("count", 1))

    if not product_id or not quantity_variant:
        return JsonResponse({"success": False, "message": "Missing data"})

    # Fetch product
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({"success": False, "message": "Product not found"})

    # Out of stock check
    if product.stock == "outofstock" or product.count <= 0:
        return JsonResponse({
            "success": False,
            "message": "Product is out of stock"
        })

    # Quantity exceeds available stock
    if count > product.count:
        return JsonResponse({
            "success": False,
            "message": f"Only {product.count} items available"
        })

    # ---------- LOGGED-IN USER ----------
    if request.user.is_authenticated:
        add_to_db_cart(request.user, product_id, quantity_variant, count)

        cart_count = (
            CartItem.objects
            .filter(cart__user=request.user)
            .aggregate(total=Sum("count"))["total"] or 0
        )

    # ---------- GUEST USER ----------
    else:
        add_to_cart(request, product_id, quantity_variant, count)

        cart_count = sum(
            item["count"]
            for item in request.session.get("cart", {}).values()
        )

    return JsonResponse({
        "success": True,
        "cart_count": cart_count
    })


@login_required(login_url="web:login")
def buy_now(request):
    if request.method != "POST":
        return redirect("web:index")

    product_id = request.POST.get("product_id")
    quantity_variant = request.POST.get("quantity")
    count = int(request.POST.get("count", 1))

    if not product_id or not quantity_variant:
        return redirect("web:index")

    # ✅ Clear existing cart (Buy Now = single product)
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart.items.all().delete()

    # ✅ Add selected product
    add_to_db_cart(
        request.user,
        product_id,
        quantity_variant,
        count
    )

    # ✅ DIRECT TO CHECKOUT
    return redirect("web:checkout")



def cart(request):

    # ---------- LOGGED-IN USER ----------
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        items = cart.items.select_related("product") if cart else []

        subtotal = Decimal("0.00")
        discount = Decimal("0.00")
        mrp_total = Decimal("0.00")

        for item in items:
            product = item.product

            # Use offer_price only if valid, else use original_price
            if product.offer_price and product.offer_price > 0:
                item.price = product.offer_price
            else:
                item.price = product.original_price

            # Subtotal using updated item.price
            subtotal += item.subtotal
            mrp_total += product.original_price * item.count

            # discount calculation safe
            discount += (product.original_price - item.price) * item.count

            # Discount percent (only show if offer_price exists)
            item.discount_percent = product.discount_percentage if product.offer_price and product.offer_price > 0 else 0

        grand_total = mrp_total - discount

        return render(request, "web/cart.html", {
            "cart_items": items,
            "subtotal": subtotal,
            "discount": discount,
            "mrp_total": mrp_total,
            "grand_total": grand_total,
            "is_authenticated": True
        })

    # ---------- GUEST USER ----------
    session_cart = request.session.get("cart", {})
    items = []

    subtotal = Decimal("0.00")
    discount = Decimal("0.00")
    mrp_total = Decimal("0.00")

    for item in session_cart.values():
        product = Product.objects.get(id=item["product_id"])

        original_price = product.original_price

        #  Use offer_price only if valid
        if product.offer_price and product.offer_price > 0:
            current_price = product.offer_price
        else:
            current_price = original_price

        item_subtotal = current_price * item["count"]

        subtotal += item_subtotal
        mrp_total += original_price * item["count"]

        discount += (original_price - current_price) * item["count"]

        items.append({
            "product_id": product.id,
            "name": product.product_name,
            "image": product.thumbnail.url,
            "quantity": item["quantity"],
            "count": item["count"],
            "price": current_price,
            "subtotal": item_subtotal,
            "original_price": original_price,
            "discount_percent": product.discount_percentage if product.offer_price and product.offer_price > 0 else 0,
        })

    grand_total = mrp_total - discount

    return render(request, "web/cart.html", {
        "cart_items": items,
        "subtotal": subtotal,
        "discount": discount,
        "mrp_total": mrp_total,
        "grand_total": grand_total,
        "is_authenticated": False
    })


def update_cart_item(request):
    if request.method != "POST":
        return JsonResponse({"success": False})

    product_id = request.POST.get("product_id")
    quantity = request.POST.get("quantity")
    count = int(request.POST.get("count", 1))

    if not product_id or not quantity:
        return JsonResponse({"success": False})

    # ---------- Logged-in user ----------
    if request.user.is_authenticated:
        cart_item = CartItem.objects.filter(
            cart__user=request.user,
            product_id=product_id,
            quantity=quantity
        ).first()

        if not cart_item:
            return JsonResponse({"success": False})

        if count <= 0:
            cart_item.delete()
        else:
            cart_item.count = count
            cart_item.save()

        cart_count = (
            CartItem.objects
            .filter(cart__user=request.user)
            .aggregate(total=Sum("count"))["total"] or 0
        )

    # ---------- Guest user ----------
    else:
        update_cart(request, product_id, quantity, count)

        cart_count = sum(
            item["count"]
            for item in request.session.get("cart", {}).values()
        )

    return JsonResponse({
        "success": True,
        "cart_count": cart_count
    })


def remove_cart_item(request):
    if request.method != "POST":
        return JsonResponse({"success": False})

    product_id = request.POST.get("product_id")
    quantity = request.POST.get("quantity")

    if not product_id or not quantity:
        return JsonResponse({"success": False})

    # ---------- Logged-in user ----------
    if request.user.is_authenticated:
        CartItem.objects.filter(
            cart__user=request.user,
            product_id=product_id,
            quantity=quantity
        ).delete()

        cart_count = (
            CartItem.objects
            .filter(cart__user=request.user)
            .aggregate(total=Sum("count"))["total"] or 0
        )

    # ---------- Guest user ----------
    else:
        remove_from_cart(request, product_id, quantity)

        cart_count = sum(
            item["count"]
            for item in request.session.get("cart", {}).values()
        )

    return JsonResponse({
        "success": True,
        "cart_count": cart_count
    })



@login_required(login_url="web:login")
def checkout(request):
    cart = Cart.objects.filter(user=request.user).first()
    items = cart.items.select_related("product") if cart else []

    if not items:
        return redirect("web:cart")

    subtotal = Decimal("0.00")
    mrp_total = Decimal("0.00")
    total_items = 0

    for item in items:
        product = item.product

        # ✅ Fix price: if offer_price not available, use original_price
        if product.offer_price and product.offer_price > 0:
            item.price = product.offer_price
        else:
            item.price = product.original_price

        # ✅ Use subtotal property (no need to set)
        subtotal += item.subtotal

        mrp_total += product.original_price * item.count
        total_items += item.count

        # ✅ send discount percent to template
        item.discount_percent = product.discount_percentage

    discount = mrp_total - subtotal
    shipping_charge = Decimal("0.00")
    payable_total = subtotal + shipping_charge

    if request.method == "POST":
        order = Order.objects.create(
            user=request.user,
            order_id=f"KM-{uuid.uuid4().hex[:10].upper()}",
            subtotal=subtotal,
            discount=discount,
            shipping_charge=shipping_charge,
            total_amount=payable_total,
            status="created"
        )

        for item in items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity_variant=item.quantity,
                count=item.count,
                price=item.price,  # ✅ correct now
                original_price=item.product.original_price,
            )

        ShippingAddress.objects.create(
            order=order,
            full_name=request.POST.get("full_name"),
            phone=request.POST.get("phone"),
            address=request.POST.get("address"),
            city=request.POST.get("city"),
            state=request.POST.get("state"),
            pincode=request.POST.get("pincode"),
            country=request.POST.get("country", "India"),
            notes=request.POST.get("notes"),
        )

        return redirect("web:payment", order_id=order.id)

    return render(request, "web/checkout.html", {
        "cart_items": items,
        "subtotal": subtotal,
        "mrp_total": mrp_total,
        "discount": discount,
        "payable_total": payable_total,
        "total_items": total_items,
    })




# @login_required
# def payment(request, order_id):
#     order = Order.objects.get(id=order_id, user=request.user)

#     client = razorpay.Client(
#         auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
#     )

#     # ✅ ROUND TO NEAREST RUPEE FIRST
#     rounded_amount = order.total_amount.quantize(
#         Decimal("1"),
#         rounding=ROUND_HALF_UP
#     )

#     # ✅ CONVERT TO PAISE (INTEGER)
#     razorpay_amount = int(rounded_amount * 100)

#     razorpay_order = client.order.create({
#         "amount": razorpay_amount,
#         "currency": "INR",
#         "payment_capture": 1
#     })

#     # ✅ SAVE ROUNDING-CONSISTENT VALUE
#     order.total_amount = rounded_amount
#     order.razorpay_order_id = razorpay_order["id"]
#     order.save()

#     return render(request, "web/payment.html", {
#         "order": order,
#         "razorpay_key": settings.RAZORPAY_KEY_ID,
#         "razorpay_order_id": razorpay_order["id"],
#         "razorpay_amount": razorpay_amount,
#     })



@login_required
def payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # order items
    order_items = order.items.select_related("product").all()

    # calculate totals dynamically
    subtotal = Decimal("0.00")
    mrp_total = Decimal("0.00")
    total_items = 0

    for item in order_items:
        subtotal += Decimal(item.price) * item.count
        mrp_total += Decimal(item.original_price) * item.count
        total_items += item.count

    discount = mrp_total - subtotal

    # you can set fixed / dynamic shipping
    delivery = Decimal("0.00")

    total_payable = subtotal + delivery

    # ROUND TO NEAREST RUPEE FIRST
    rounded_amount = total_payable.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    # Razorpay expects paise integer
    razorpay_amount = int(rounded_amount * 100)

    # Razorpay order create
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    razorpay_order = client.order.create({
        "amount": razorpay_amount,
        "currency": "INR",
        "payment_capture": 1
    })

    # save values in DB
    order.subtotal = subtotal
    order.discount = discount
    order.shipping_charge = delivery
    order.total_amount = rounded_amount
    order.razorpay_order_id = razorpay_order["id"]
    order.save()

    return render(request, "web/payment.html", {
        "order": order,
        "order_items": order_items,
        "total_items": total_items,
        "subtotal": subtotal,
        "mrp_total": mrp_total,
        "discount": discount,
        "delivery": delivery,
        "total_payable": rounded_amount,

        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "razorpay_order_id": razorpay_order["id"],
        "razorpay_amount": razorpay_amount,
    })

@login_required
def payment_success(request):
    if request.method != "POST":
        return redirect("web:index")

    payment_id = request.POST.get("razorpay_payment_id")
    razorpay_order_id = request.POST.get("razorpay_order_id")
    signature = request.POST.get("razorpay_signature")

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    # ✅ Verify payment
    client.utility.verify_payment_signature({
        "razorpay_order_id": razorpay_order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": signature
    })

    order = get_object_or_404(
        Order,
        razorpay_order_id=razorpay_order_id,
        user=request.user
    )

    # ✅ Prevent double processing
    if order.payment_status:
        return redirect("web:order_success", order_id=order.id)

    with transaction.atomic():
        # ✅ Mark order paid
        order.payment_status = True
        order.status = "paid"
        order.payment_id = payment_id
        order.save()

        # ✅ UPDATE PRODUCT STOCK
        for item in order.items.select_related("product"):
            product = item.product

            # Reduce stock count
            product.count -= item.count

            # Safety: no negative stock
            if product.count <= 0:
                product.count = 0
                product.stock = "outofstock"
            else:
                product.stock = "instock"

            product.save()

        # ✅ Clear cart
        if hasattr(order.user, "cart"):
            order.user.cart.items.all().delete()

        request.session["send_invoice"] = order.id

    return redirect("web:order_success", order_id=order.id)



def send_order_email(order):
    message = f"""
Order ID: {order.order_id}
Total: ₹{order.total_amount}

Shipping Address:
{order.shipping.full_name}
{order.shipping.address}
{order.shipping.city}, {order.shipping.state}
{order.shipping.pincode}

Notes: {order.shipping.notes or "None"}
"""

    send_mail(
        subject="Your Kanthi Mantra Order Confirmation",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.user.email],
    )


@login_required
def generate_invoice(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)

    template = get_template("web/invoice.html")
    html = template.render({"order": order})

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="invoice_{order.order_id}.pdf"'

    pisa.CreatePDF(html, dest=response)
    return response


@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    return render(request, "web/order_success.html", {
        "order": order
    })


@login_required
def invoice_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # ✅ Send invoice once, AFTER page loads
    if request.session.get("send_invoice") == order.id:
        try:
            send_invoice_email(order)
        except Exception as e:
            print("Invoice email failed:", e)

        del request.session["send_invoice"]

    return render(request, "web/invoice.html", {
        "order": order,
        "items": order.items.all(),
    })


def gallery(request):
    return render(request, "web/gallery.html")

def terms_and_conditions(request):
    return render(request,"web/terms_and_conditions.html")


def privacy_policy(request):
    return render(request,"web/privacy_policy.html")

#------------------------------------------------#
#-------------ADMIN PANEL VIEWS -----------------#
#------------------------------------------------#

#----admin-login----
def admin_login(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, username=email, password=password)

        if user is not None:
            if user.is_superuser:
                login(request, user)
                return redirect('web:admin_dashboard')  # change if needed
            else:
                messages.error(request, "You are not authorized as admin.")
        else:
            messages.error(request, "Invalid email or password.")

    return render(request, 'adminpanel/admin_login.html')


def admin_logout(request):
    logout(request)
    return redirect('web:admin_login')


def admin_dashboard(request):
    total_orders = Order.objects.count()
    total_customers = User.objects.filter(is_superuser=False).count()
    total_products = Product.objects.count()

    # ✅ FETCH categories (not count)
    categories = Category.objects.all().order_by('-created_at')

    total_revenue = (
        Order.objects
        .filter(payment_status=True)
        .aggregate(total=Sum("total_amount"))["total"]
        or 0
    )

    context = {
        "total_orders": total_orders,
        "total_customers": total_customers,
        "total_products": total_products,
        "categories": categories,
        "total_revenue": total_revenue,
    }

    return render(request, "adminpanel/dashboard.html", context)



@login_required(login_url='web:admin_login')
def admin_settings(request):
    user = request.user
    profile, created = AdminProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        user.first_name = request.POST.get("name")
        user.email = request.POST.get("email")
        profile.phone = request.POST.get("phone")

        if 'profile_image' in request.FILES:
            profile.profile_image = request.FILES['profile_image']

        user.save()
        profile.save()

        messages.success(request, "Profile updated successfully")
        return redirect('web:admin_settings')

    return render(request, 'adminpanel/admin_settings.html', {
        "user": user,
        "account": profile   # keeping template unchanged
    })


# Category list
def category_list(request):
    """List all categories."""
    categories = Category.objects.all()
    return render(request, 'adminpanel/category_list.html', {'categories': categories})


# Add category
def add_category(request):
    if request.method == 'POST':

        # ✅ Normalize input (THIS IS CRITICAL)
        category_name = request.POST.get('category_name', '')
        category_name = category_name.strip()              # remove spaces
        category_name = category_name.title()              # normalize case

        short_description = request.POST.get('short_description')
        thumbnail = request.FILES.get('thumbnail')
        category_image = request.FILES.get('category_image')

        if not category_name:
            messages.error(request, 'Category name is required')
            return redirect('web:add_category')

        # ✅ REAL duplicate protection
        if Category.objects.filter(category_name__iexact=category_name).exists():
            messages.error(request, 'Category already exists')
            return redirect('web:add_category')

        Category.objects.create(
            category_name=category_name,
            short_description=short_description,
            thumbnail=thumbnail,
            category_image=category_image
        )

        messages.success(request, f'Category "{category_name}" added successfully')
        return redirect('web:category_list')

    return render(request, 'adminpanel/add_category.html')


# Edit category
def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        category_name = request.POST.get('category_name')
        short_description = request.POST.get('short_description')
        thumbnail = request.FILES.get('thumbnail')
        category_image = request.FILES.get('category_image')

        if not category_name:
            messages.error(request, 'Category name is required')
            return redirect('web:edit_category', category_id=category_id)

        if Category.objects.filter(category_name=category_name).exclude(id=category_id).exists():
            messages.error(request, 'Category name already exists')
            return redirect('web:edit_category', category_id=category_id)

        category.category_name = category_name
        category.short_description = short_description

        if thumbnail:
            category.thumbnail = thumbnail
        if category_image:
            category.category_image = category_image

        category.save()
        messages.success(request, 'Category updated successfully')
        return redirect('web:category_list')

    return render(request, 'adminpanel/edit_category.html', {'category': category})


# Delete category
def delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        category_name = category.category_name
        category.delete()
        messages.success(request, f'Category "{category_name}" deleted successfully')
        return redirect('web:category_list')

    return render(request, 'adminpanel/delete_category.html', {'category': category})

# View category
def view_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    return render(request, 'adminpanel/view_category.html', {'category': category})



# ----SubCategory----
def sub_category_add(request):
    categories = Category.objects.all()

    if request.method == 'POST':
        category_id = request.POST.get('category')
        sub_category_name = request.POST.get('sub_category_name', '').strip().title()
        sub_category_image = request.FILES.get('sub_category_image')

        if not sub_category_name:
            messages.error(request, 'Sub category name is required')
            return redirect('web:add_sub_category')  # ✅ FIXED

        category = Category.objects.get(id=category_id)

        if SubCategory.objects.filter(
            category=category,
            sub_category_name__iexact=sub_category_name
        ).exists():
            messages.error(
                request,
                f'Sub Category "{sub_category_name}" already exists in {category.category_name}'
            )
            return redirect('web:add_sub_category')  # ✅ FIXED

        SubCategory.objects.create(
            category=category,
            sub_category_name=sub_category_name,
            sub_category_image=sub_category_image
        )

        messages.success(request, 'Sub Category added successfully')
        return redirect('web:sub_category_list')

    return render(
        request,
        'adminpanel/add_sub_category.html',
        {'categories': categories}
    )


def sub_category_list(request):

    subcategories = SubCategory.objects.all()
    return render(request, 'adminpanel/sub_category_list.html',
                   {'subcategories': subcategories})


def sub_category_edit(request, id):
    subcategory = SubCategory.objects.get(id=id)
    categories = Category.objects.all()

    if request.method == 'POST':
        category_id = request.POST.get('category')
        sub_category_name = request.POST.get('sub_category_name')
        sub_category_image = request.FILES.get('sub_category_image')

        subcategory.category = Category.objects.get(id=category_id)
        subcategory.sub_category_name = sub_category_name

        if sub_category_image:
            subcategory.sub_category_image = sub_category_image

        subcategory.save()

        messages.success(request, 'Sub Category updated successfully')
        return redirect('web:sub_category_list')

    return render(
        request,
        'adminpanel/edit_sub_category.html',
        {
            'subcategory': subcategory,
            'categories': categories
        }
    )

def sub_category_delete(request, id):
    subcategory = get_object_or_404(SubCategory, id=id)
    subcategory.delete()
    messages.success(request, 'Sub Category deleted successfully')
    return redirect('web:sub_category_list')

def sub_category_view(request, id):
    subcategory = SubCategory.objects.get(id=id)
    return render(
        request,
        'adminpanel/view_sub_category.html',
        {'subcategory': subcategory}
    )


# ---Product----

# add product
def add_product(request):
    categories = Category.objects.all()
    subcategories = SubCategory.objects.all()

    if request.method == "POST":
        category = Category.objects.get(id=request.POST.get("category"))
        subcategory = SubCategory.objects.get(id=request.POST.get("subcategory"))

        stock_status = request.POST.get("stock_status")
        stock_count = int(request.POST.get("stock_quantity") or 0)

        if stock_status == "outofstock":
            stock_count = 0

        product = Product.objects.create(
            product_name=request.POST.get("product_name"),
            category=category,
            subcategory=subcategory,
            brand=request.POST.get("brand"),
            country=request.POST.get("country"),
            description=request.POST.get("description"),
            quantity=request.POST.get("quantity"),
            shelf_life=request.POST.get("shelf_life"),
            original_price=request.POST.get("original_price") or 0,
            discount_percentage=request.POST.get("discount_percentage") or 0,
            offer_price=request.POST.get("offer_price") or 0,
            stock=stock_status,
            count=stock_count,
            thumbnail=request.FILES.get("thumbnail"),
            page_title=request.POST.get("page_title"),
            meta_keywords=request.POST.get("meta_keywords"),
            meta_description=request.POST.get("meta_description"),
            canonical_tag=request.POST.get("canonical_url"),
            product_highlight=request.POST.get("highlights"),
            how_to_use=request.POST.get("how_to_use")
        )        

        # ✅ Save images
        for i, file in enumerate(request.FILES.getlist("product_images")):
            ProductImage.objects.create(
                product=product,
                media_type="image",
                media_file=file,
                display_order=i
            )

        # ✅ Save video (THIS WAS MISSING)
        video = request.FILES.get("product_video")
        if video:
            ProductImage.objects.create(
                product=product,
                media_type="video",
                media_file=video,
                display_order=100
            )

        messages.success(request, "Product added successfully!")
        return redirect("web:product_list")

    return render(request, "adminpanel/add_product.html", {
        "categories": categories,
        "subcategories": subcategories
    })

# Product list
def product_list(request):
    products = Product.objects.select_related('category').all()
    return render(request, 'adminpanel/product_list.html', {
        'products': products
    })


# edit product
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    categories = Category.objects.all()
    subcategories = SubCategory.objects.all()

    if request.method == "POST":

        # -------- BASIC FIELDS --------
        product.product_name = request.POST.get("product_name")
        product.category = Category.objects.get(id=request.POST.get("category"))
        product.subcategory = SubCategory.objects.get(id=request.POST.get("subcategory"))
        product.brand = request.POST.get("brand")
        product.country = request.POST.get("country")
        product.description = request.POST.get("description")
        product.how_to_use = request.POST.get("how_to_use")
        product.quantity = request.POST.get("quantity")
        product.shelf_life = request.POST.get("shelf_life")

        product.original_price = request.POST.get("original_price") or 0
        product.discount_percentage = request.POST.get("discount_percentage") or 0
        product.offer_price = request.POST.get("offer_price") or 0

        product.product_highlight = request.POST.get("product_highlight")
        product.page_title = request.POST.get("page_title")
        product.meta_keywords = request.POST.get("meta_keywords")
        product.meta_description = request.POST.get("meta_description")
        product.canonical_tag = request.POST.get("canonical_url")

        if request.FILES.get("thumbnail"):
            product.thumbnail = request.FILES.get("thumbnail")

        # -------- ✅ STOCK (FIXED PROPERLY) --------
        stock_value = request.POST.get("stock_status")

        if stock_value not in ["instock", "outofstock"]:
            stock_value = "instock"

        product.stock = stock_value
        product.count = int(request.POST.get("stock_quantity") or 0)

        if product.stock == "outofstock":
            product.count = 0

        # -------- SAVE ONLY ONCE --------
        product.save()

        # -------- MEDIA --------
        for i, img in enumerate(request.FILES.getlist("product_images")):
            ProductImage.objects.create(
                product=product,
                media_type="image",
                media_file=img,
                display_order=i
            )

        video = request.FILES.get("product_video")
        if video:
            ProductImage.objects.filter(
                product=product,
                media_type="video"
            ).delete()

            ProductImage.objects.create(
                product=product,
                media_type="video",
                media_file=video,
                display_order=100
            )

        messages.success(request, "Product updated successfully")
        return redirect("web:product_list")

    return render(request, "adminpanel/edit_product.html", {
        "product": product,
        "categories": categories,
        "subcategories": subcategories
    })


def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        product_name = product.product_name
        product.delete()
        messages.success(request, f'Product "{product_name}" deleted successfully')
        return redirect('web:product_list')

    return render(request, 'adminpanel/delete_product.html', {'product': product})


def view_product(request, product_id):
    product = Product.objects.get(id=product_id)

    videos = product.media_files.filter(media_type="video")
    images = product.media_files.filter(media_type="image")

    return render(request, "adminpanel/view_product.html", {
        "product": product,
        "videos": videos,
        "images": images,
    })


#--------------order-------------
def order_list(request):
    orders = Order.objects.select_related("user").order_by("-created_at")
    return render(request, "adminpanel/order_list.html", {
        "orders": orders
    })


def order_detail(request, order_id):
    order = (
        Order.objects
        .select_related("user")
        .prefetch_related(
            "items__product",   # OrderItem + Product
            "shipping"          # ShippingAddress (OneToOne)
        )
        .get(id=order_id)
    )

    return render(request, "adminpanel/order_detail.html", {
        "order": order,
    })


@require_POST
def order_delete(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.delete()
    return redirect("web:order_list")



#--------------users-------------
def all_users(request):
    users = User.objects.all()
    return render(request, 'adminpanel/all_users.html', {'users': users})



def view_user(request, user_id):
    user = get_object_or_404(User, id=user_id)

    # Default address (Account)
    account = Account.objects.filter(user=user).first()

    # User orders (for Orders tab)
    orders = Order.objects.filter(user=user).order_by('-created_at')

    context = {
        'user': user,
        'account': account,
        'orders': orders,
    }
    return render(request, 'adminpanel/view_user.html', context)


@require_POST
def admin_delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)

    # Optional safety (recommended but not mandatory)
    if user.is_superuser:
        messages.error(request, "Superuser cannot be deleted.")
        return redirect('web:all_users')

    user.delete()
    messages.success(request, "User deleted successfully.")
    return redirect('web:all_users')




#Cms Management----------------


def cms_context():
    return {
        "sliders": HomeSlider.objects.all().order_by("-id"),
        "center_banner": HomeCenterBanner.objects.first(),
        "end_banners": HomeEndBanner.objects.all().order_by("-id"),
        "flash_news": HomeFlashNews.objects.all().order_by("-id"),
        "home_video": HomeVideo.objects.first(),  # ✅ THIS LINE
    }


def cms_home(request):
    return render(request, "adminpanel/cms_home.html", cms_context())

def add_slider(request):
    if request.method == "POST":
        image = request.FILES.get("slider_image")
        if image:
            HomeSlider.objects.create(image=image)

    return redirect(f"{reverse('web:cms_home')}?tab=pills-sliders")


def edit_slider(request, pk):
    slider = get_object_or_404(HomeSlider, pk=pk)

    if request.method == "POST":
        image = request.FILES.get("slider_image")
        if image:
            slider.image.delete(save=False)
            slider.image = image
            slider.save()

        return redirect(f"{reverse('web:cms_home')}?tab=pills-sliders")

    context = cms_context()
    context["edit_slider"] = slider
    return render(request, "adminpanel/cms_home.html", context)


def delete_slider(request, pk):
    slider = get_object_or_404(HomeSlider, pk=pk)
    slider.image.delete(save=False)
    slider.delete()

    return redirect(f"{reverse('web:cms_home')}?tab=pills-sliders")


def center_banner(request):
    banner, _ = HomeCenterBanner.objects.get_or_create(id=1)

    if request.method == "POST":
        if request.FILES.get("banner1"):
            if banner.banner1:
                banner.banner1.delete(save=False)
            banner.banner1 = request.FILES.get("banner1")

        if request.FILES.get("banner2"):
            if banner.banner2:
                banner.banner2.delete(save=False)
            banner.banner2 = request.FILES.get("banner2")

        if request.FILES.get("banner3"):
            if banner.banner3:
                banner.banner3.delete(save=False)
            banner.banner3 = request.FILES.get("banner3")

        banner.save()
        return redirect(f"{reverse('web:cms_home')}?tab=banner")
    

def delete_center_banner(request, field):
    banner = HomeCenterBanner.objects.first()
    if not banner:
        return redirect(reverse("web:cms_home"))

    if field == "banner1" and banner.banner1:
        banner.banner1.delete(save=False)
        banner.banner1 = None

    elif field == "banner2" and banner.banner2:
        banner.banner2.delete(save=False)
        banner.banner2 = None

    elif field == "banner3" and banner.banner3:
        banner.banner3.delete(save=False)
        banner.banner3 = None

    banner.save()
    return redirect(f"{reverse('web:cms_home')}?tab=banner")

def home_video(request):
    HomeVideo.objects.exclude(id=1).delete()
    video, _ = HomeVideo.objects.get_or_create(id=1)

    if request.method == "POST":
        if request.FILES.get("thumbnail"):
            if video.thumbnail:
                video.thumbnail.delete(save=False)
            video.thumbnail = request.FILES.get("thumbnail")

        if request.FILES.get("video_file"):
            if video.video_file:
                video.video_file.delete(save=False)
            video.video_file = request.FILES.get("video_file")

        video.save()
        return redirect(f"{reverse('web:cms_home')}?tab=video")

    context = cms_context()
    context["home_video"] = video
    return render(request, "adminpanel/cms_home.html", context)

def delete_home_video_file(request, file_type):
    video = get_object_or_404(HomeVideo, id=1)

    if file_type == "video" and video.video_file:
        video.video_file.delete(save=True)

    if file_type == "thumbnail" and video.thumbnail:
        video.thumbnail.delete(save=True)

    return redirect(f"{reverse('web:cms_home')}?tab=video")

def add_end_banner(request):
    if request.method == "POST":
        images = request.FILES.getlist("end_banner_images")
        for img in images:
            HomeEndBanner.objects.create(image=img)

    return redirect(f"{reverse('web:cms_home')}?tab=endbanner")

def edit_end_banner(request, banner_id):
    banner = get_object_or_404(HomeEndBanner, id=banner_id)

    if request.method == "POST":
        if request.FILES.get("end_banner_image"):
            banner.image.delete(save=False)
            banner.image = request.FILES.get("end_banner_image")
            banner.save()

        return redirect(f"{reverse('web:cms_home')}?tab=endbanner")

    context = cms_context()
    context["edit_end_banner"] = banner
    return render(request, "adminpanel/cms_home.html", context)

def delete_end_banner(request, banner_id):
    banner = get_object_or_404(HomeEndBanner, id=banner_id)
    banner.image.delete(save=False)
    banner.delete()

    return redirect(f"{reverse('web:cms_home')}?tab=endbanner")

def add_edit_flash_news(request, news_id=None):
    edit_news = None

    if news_id:
        edit_news = get_object_or_404(HomeFlashNews, id=news_id)

    if request.method == "POST":
        news_list = request.POST.getlist("flash_news[]")

        if edit_news:
            if news_list and news_list[0].strip():
                edit_news.text = news_list[0].strip()
                edit_news.save()
        else:
            for text in news_list:
                text = text.strip()
                if text:
                    HomeFlashNews.objects.create(text=text)

        return redirect(f"{reverse('web:cms_home')}?tab=flashnews")

    context = cms_context()
    context["edit_flash_news"] = edit_news
    return render(request, "adminpanel/cms_home.html", context)

def delete_flash_news(request, news_id):
    news = get_object_or_404(HomeFlashNews, id=news_id)
    news.delete()

    return redirect(f"{reverse('web:cms_home')}?tab=flashnews")



#  Auto add https:// if missing
def fix_url(url):
    if url:
        url = url.strip()
        if url and not url.startswith(("http://", "https://")):
            return "https://" + url
    return url




def fix_map_embed_url(url):
    """
    Convert Google map link to iframe-safe embed link.
    """
    if not url:
        return ""

    url = url.strip()

    # if already embed url
    if "google.com/maps/embed" in url:
        return url

    # if user pasted normal Google map url
    if "google.com/maps" in url or "maps.google.com" in url:
        # create embed search url using query
        return f"https://www.google.com/maps?q={quote(url)}&output=embed"

    # if user pasted just place name like "Ernakulam"
    return f"https://www.google.com/maps?q={quote(url)}&output=embed"


@require_http_methods(["GET", "POST"])
def cms_contact(request):
    contact, _ = ContactPage.objects.get_or_create(id=1)

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "basic":
            # Banner
            banner = request.FILES.get("banner")
            if banner:
                contact.banner = banner

            # Text fields
            contact.banner_heading = request.POST.get("banner_heading", "").strip()
            contact.banner_paragraph = request.POST.get("banner_paragraph", "").strip()
            contact.office_address = request.POST.get("office_address", "").strip()

            # ✅ Phone numbers (FIXED)
            contact.phone1 = request.POST.get("phone1", "").strip()
            contact.phone2 = request.POST.get("phone2", "").strip()

            contact.email1 = request.POST.get("email1", "").strip()
            contact.email2 = request.POST.get("email2", "").strip()

            contact.location_map_link = fix_map_embed_url(request.POST.get("location_map_link"))

            contact.save()
            messages.success(request, "Contact basic info updated successfully!")
            return redirect("web:cms_contact")

        elif form_type == "social":
            contact.instagram = fix_url(request.POST.get("instagram"))
            contact.facebook = fix_url(request.POST.get("facebook"))
            contact.linkedin = fix_url(request.POST.get("linkedin"))
            contact.youtube = fix_url(request.POST.get("youtube"))
            contact.x = fix_url(request.POST.get("x"))

            contact.save()
            messages.success(request, "Social media links updated successfully!")
            return redirect("web:cms_contact")

        else:
            messages.error(request, "Invalid request.")
            return redirect("web:cms_contact")

    return render(request, "adminpanel/cms_contact.html", {"contact": contact})




def cms_legal(request):
    return render(request, "adminpanel/cms_legal.html")

def cms_blogs(request):
    return render(request, "adminpanel/cms_blogs.html")

