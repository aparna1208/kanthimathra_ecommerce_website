from decimal import Decimal, ROUND_HALF_UP
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from .models import CartItem, PendingRegistration, EmailOTP, Category, Product, ProductImage, SubCategory, Wishlist, Cart, Order, OrderItem, ShippingAddress
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import EmailOTP
from django.contrib.auth.hashers import make_password
from .models import EmailOTP, PendingRegistration, Account
from .utils import send_otp_email
from django.contrib.auth import get_user_model 
from django.contrib.auth import logout
import random
from django.views.decorators.http import require_POST
from .utils import add_to_cart, cart_totals, merge_session_cart_to_db, add_to_db_cart, update_cart, remove_from_cart
from django.db.models import Sum
import razorpay
from django.core.mail import send_mail
from reportlab.pdfgen import canvas
from django.http import HttpResponse
import uuid
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.core.paginator import Paginator
from .utils import send_invoice_email




User = get_user_model()


#------------------------------------------------#
#-------------WEB FRONTEND VIEWS-----------------#
#------------------------------------------------#


def index(request):
    categories = Category.objects.all()
    products = Product.objects.all()[:8]

    wishlist_ids = []

    if request.user.is_authenticated:
        wishlist_ids = Wishlist.objects.filter(
            user=request.user
        ).values_list("product_id", flat=True)

    context = {
        'categories': categories,
        'products': products,
        'wishlist_ids': wishlist_ids,   # ✅ added correctly
    }

    return render(request, 'web/index.html', context)

@login_required(login_url='web:login')
def account(request):
    return render(request, 'web/account.html')


def address(request):
    return render(request, 'web/address.html')


def account_settings(request):
    return render(request, 'web/settings.html')

def order_history(request):
    return render(request, 'web/orders.html')




def blog(request):
    return render(request, 'web/blog.html')


def blog_single(request):
    return render(request, 'web/blog-single.html')


def contact(request):
    return render(request, 'web/contact.html')


def about(request):
    return render(request, 'web/about.html')


def category(request):
    cat = Category.objects.all()
    return render(request, 'web/category.html', {'categories': cat})

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



#------------- CART VIEWS -----------------#
def add_to_cart_view(request):
    if request.method != "POST":
        return JsonResponse({"success": False})

    product_id = request.POST.get("product_id")
    quantity_variant = request.POST.get("quantity")
    count = int(request.POST.get("count", 1))

    if not product_id or not quantity_variant:
        return JsonResponse({"success": False})

    if request.user.is_authenticated:
        add_to_db_cart(request.user,product_id, quantity_variant,count)

        cart_count = (CartItem.objects.filter(cart__user=request.user) .aggregate(total=Sum("count"))["total"] or 0)
    else:
        add_to_cart(request,product_id,quantity_variant,count)

        cart_count = sum(
            item["count"]
            for item in request.session.get("cart", {}).values()
        )

    # ✅ JSON ONLY (NO REDIRECT)
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



# def cart(request):
#     # ---------- Logged-in user ----------
#     if request.user.is_authenticated:
#         cart = Cart.objects.filter(user=request.user).first()
#         items = cart.items.all() if cart else []

#         subtotal = Decimal("0.00")     # offer price total
#         discount = Decimal("0.00")     # discount amount
#         mrp_total = Decimal("0.00")    # original price total

#         for item in items:
#             subtotal += item.subtotal
#             mrp_total += item.product.original_price * item.count

#             discount += (
#                 item.product.original_price - item.price
#             ) * item.count

#             # attach discount percentage
#             item.discount_percent = item.product.discount_percentage

#         grand_total = mrp_total - discount

#         return render(request, "web/cart.html", {
#             "cart_items": items,
#             "subtotal": subtotal,
#             "discount": discount,
#             "mrp_total": mrp_total,          # ✅ NEW
#             "grand_total": grand_total,      # ✅ NEW
#             "is_authenticated": True
#         })

#     # ---------- Guest user ----------
#     session_cart = request.session.get("cart", {})
#     items = []

#     subtotal = Decimal("0.00")
#     discount = Decimal("0.00")
#     mrp_total = Decimal("0.00")

#     for item in session_cart.values():
#         product = Product.objects.get(id=item["product_id"])

#         item_subtotal = Decimal(item["price"]) * item["count"]
#         subtotal += item_subtotal

#         mrp_total += product.original_price * item["count"]

#         discount += (
#             product.original_price - Decimal(item["price"])
#         ) * item["count"]

#         item_data = item.copy()
#         item_data["subtotal"] = item_subtotal
#         item_data["original_price"] = product.original_price
#         item_data["discount_percent"] = product.discount_percentage

#         items.append(item_data)

#     grand_total = mrp_total - discount

#     return render(request, "web/cart.html", {
#         "cart_items": items,
#         "subtotal": subtotal,
#         "discount": discount,
#         "mrp_total": mrp_total,          # ✅ NEW
#         "grand_total": grand_total,      # ✅ NEW
#         "is_authenticated": False
#     })



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

            # ✅ Always use latest price (runtime only)
            item.price = product.offer_price

            subtotal += item.subtotal  # uses @property
            mrp_total += product.original_price * item.count

            discount += (
                product.original_price - product.offer_price
            ) * item.count

            item.discount_percent = product.discount_percentage

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

        current_price = product.offer_price
        original_price = product.original_price

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
            "discount_percent": product.discount_percentage,
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
    items = cart.items.all() if cart else []

    if not items:
        return redirect("web:cart")

    subtotal = Decimal("0.00")
    mrp_total = Decimal("0.00")
    total_items = 0  # ✅ ADD THIS

    for item in items:
        subtotal += item.subtotal
        mrp_total += item.product.original_price * item.count
        total_items += item.count  # ✅ SUM QUANTITY

    discount = mrp_total - subtotal
    shipping_charge = Decimal("0.00")
    payable_total = subtotal + shipping_charge

    if request.method == "POST":
        ...
        return redirect("web:payment", order_id=order.id)

    return render(request, "web/checkout.html", {
        "cart_items": items,
        "subtotal": subtotal,
        "mrp_total": mrp_total,
        "discount": discount,
        "payable_total": payable_total,
        "total_items": total_items,  # ✅ PASS TO TEMPLATE
    })


@login_required
def payment(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    # ✅ ROUND TO NEAREST RUPEE FIRST
    rounded_amount = order.total_amount.quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP
    )

    # ✅ CONVERT TO PAISE (INTEGER)
    razorpay_amount = int(rounded_amount * 100)

    razorpay_order = client.order.create({
        "amount": razorpay_amount,
        "currency": "INR",
        "payment_capture": 1
    })

    # ✅ SAVE ROUNDING-CONSISTENT VALUE
    order.total_amount = rounded_amount
    order.razorpay_order_id = razorpay_order["id"]
    order.save()

    return render(request, "web/payment.html", {
        "order": order,
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "razorpay_order_id": razorpay_order["id"],
        "razorpay_amount": razorpay_amount,
    })


# @login_required
# def payment_success(request):
#     if request.method == "POST":
#         payment_id = request.POST.get("razorpay_payment_id")
#         razorpay_order_id = request.POST.get("razorpay_order_id")
#         signature = request.POST.get("razorpay_signature")

#         client = razorpay.Client(
#             auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
#         )

#         try:
#             client.utility.verify_payment_signature({
#                 "razorpay_order_id": razorpay_order_id,
#                 "razorpay_payment_id": payment_id,
#                 "razorpay_signature": signature
#             })
#         except:
#             return HttpResponse("Payment verification failed", status=400)

#         order = Order.objects.get(razorpay_order_id=razorpay_order_id)

#         order.payment_status = True
#         order.status = "paid"
#         order.payment_id = payment_id
#         order.save()

#         # clear cart
#         order.user.cart.items.all().delete()

#         send_order_email(order)

#         return redirect("web:invoice_view", order_id=order.id)

# @login_required
# def payment_success(request):
#     if request.method == "POST":
#         payment_id = request.POST.get("razorpay_payment_id")
#         razorpay_order_id = request.POST.get("razorpay_order_id")
#         signature = request.POST.get("razorpay_signature")

#         client = razorpay.Client(
#             auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
#         )

#         try:
#             client.utility.verify_payment_signature({
#                 "razorpay_order_id": razorpay_order_id,
#                 "razorpay_payment_id": payment_id,
#                 "razorpay_signature": signature
#             })
#         except:
#             return HttpResponse("Payment verification failed", status=400)

#         order = get_object_or_404(
#             Order,
#             razorpay_order_id=razorpay_order_id,
#             user=request.user
#         )

#         order.payment_status = True
#         order.status = "paid"
#         order.payment_id = payment_id
#         order.save()

#         # ✅ clear cart
#         order.user.cart.items.all().delete()

#         send_order_email(order)

#         # ✅ STEP 1: ORDER SUCCESS PAGE
#         return redirect("web:order_success", order_id=order.id)



# @login_required
# def payment_success(request):
#     if request.method == "POST":
#         payment_id = request.POST.get("razorpay_payment_id")
#         razorpay_order_id = request.POST.get("razorpay_order_id")
#         signature = request.POST.get("razorpay_signature")

#         client = razorpay.Client(
#             auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
#         )

#         client.utility.verify_payment_signature({
#             "razorpay_order_id": razorpay_order_id,
#             "razorpay_payment_id": payment_id,
#             "razorpay_signature": signature
#         })

#         order = Order.objects.get(
#             razorpay_order_id=razorpay_order_id,
#             user=request.user
#         )

#         order.payment_status = True
#         order.status = "paid"
#         order.payment_id = payment_id
#         order.save()

#         # Clear cart
#         order.user.cart.items.all().delete()

#         # ✅ SEND SAME INVOICE.HTML AS PDF MAIL
#         send_invoice_email(order)

#         return redirect("web:order_success", order_id=order.id)


# working--
# @login_required
# def payment_success(request):
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

    # ✅ Prevent double execution
    if not order.payment_status:
        order.payment_status = True
        order.status = "paid"
        order.payment_id = payment_id
        order.save()

        # Clear cart
        if hasattr(order.user, "cart"):
            order.user.cart.items.all().delete()

        # Send invoice email
        try:
            send_invoice_email(order)
        except Exception as e:
            print("Invoice mail failed:", e)

    # ✅ DIRECT REDIRECT (NO PAYMENT PAGE AGAIN)
    return redirect("web:invoice_view", order_id=order.id)




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

    if not order.payment_status:
        order.payment_status = True
        order.status = "paid"
        order.payment_id = payment_id
        order.save()

        if hasattr(order.user, "cart"):
            order.user.cart.items.all().delete()

        # 🔥 DO NOT SEND MAIL HERE
        request.session["send_invoice"] = order.id

    # 🚀 FAST redirect (NO delay)
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



# @login_required
# def order_success(request, order_id):
#     order = Order.objects.get(id=order_id, user=request.user)

#     return render(request, "web/order_success.html", {
#         "order": order
#     })



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

#------------------------------------------------#
#-------------ADMIN PANEL VIEWS -----------------#
#------------------------------------------------#



def admin_dashboard(request):
    return render(request, 'adminpanel/dashboard.html')




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
    product = get_object_or_404(
        Product.objects.select_related("category", "subcategory")
                       .prefetch_related("media_files"),
        id=product_id
    )

    return render(request,"adminpanel/view_product.html",
        {
            "product": product
        }
    )