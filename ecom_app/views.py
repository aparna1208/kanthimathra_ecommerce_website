from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from .models import PendingRegistration, EmailOTP




#------------------------------------------------#
#-------------WEB FRONTEND VIEWS-----------------#
#------------------------------------------------#



def index(request):
    return render(request, 'web/index.html')


def register_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm = request.POST.get('confirm_password')

        if not email or not password or not confirm:
            messages.error(request, 'Please fill all fields')
            return redirect('register')

        if password != confirm:
            messages.error(request, 'Passwords do not match')
            return redirect('register')

        # create OTP first
        otp_obj = EmailOTP.objects.create(email=email)

        # create or update pending registration
        pending = PendingRegistration.objects.filter(email=email).first()
        if pending:
            pending.otp = otp_obj
            pending.set_password(password)
            pending.is_verified = False
            pending.save()
        else:
            pending = PendingRegistration.objects.create(email=email, password_hash='', otp=otp_obj)
            pending.set_password(password)

        # send OTP email
        subject = 'Your verification code'
        message = f'Your verification code is: {otp_obj.otp}\nThis code expires in 3 minutes.'
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'EMAIL_HOST_USER', None)
        send_mail(subject, message, from_email, [email], fail_silently=False)

        messages.success(request, 'Verification code sent to your email')
        return redirect('verify_otp')

    return render(request, 'register.html')

def otp_expiry_time():
    return timezone.now() + timezone.timedelta(minutes=3)

def verify_otp_view(request):
    """Verify OTP and finalize registration."""
    if request.method == 'GET':
        return render(request, 'verify_otp.html')

    email = request.POST.get('email')
    code = (request.POST.get('otp') or '').strip()

    if not email or not code:
        messages.error(request, 'Please provide both email and OTP')
        return redirect('verify_otp')

    otp = EmailOTP.objects.filter(email=email).order_by('-created_at').first()
    pending = PendingRegistration.objects.filter(email=email).first()

    if not otp or not pending or otp.is_expired() or otp.otp != code:
        if otp and otp.otp != code:
            otp.attempts = otp.attempts + 1
            otp.save()
        messages.error(request, 'Invalid or expired OTP')
        return redirect('verify_otp')

    otp.mark_verified()
    pending.is_verified = True
    pending.save()

    user = pending.check_verified_and_create_user()
    if user:
        messages.success(request, 'Registration complete')
        return redirect('index')

    messages.error(request, 'Failed to create account; contact support')
    return redirect('verify_otp')




def resend_otp_view(request):
    """Create & send a fresh OTP for a pending registration."""
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            pending = PendingRegistration.objects.get(email=email)
        except PendingRegistration.DoesNotExist:
            messages.error(request, 'No pending registration found')
            return redirect('register')

        otp_obj = EmailOTP.objects.create(email=email)
        pending.otp = otp_obj
        pending.save()

        subject = 'Your new verification code'
        message = f'Your verification code is: {otp_obj.otp}\nThis code expires in 3 minutes.'
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'EMAIL_HOST_USER', None)
        send_mail(subject, message, from_email, [email], fail_silently=False)

        messages.success(request, 'New verification code sent')
        return redirect('verify_otp')

    return redirect('register')


def login_view(request):
    """Authenticate user using email and password."""
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Successfully logged in')
            return redirect('index')

        messages.error(request, 'Invalid email or password')
        return redirect('login')

    return render(request, 'login.html')





#------------------------------------------------#
#-------------ADMIN PANEL VIEWS -----------------#
#------------------------------------------------#


# Add category
def admin_dashboard(request):
    return render(request, 'adminpanel/dashboard.html')

def add_category(request):
    return render(request, 'adminpanel/add_category.html')

def category_list(request):
    return render(request, 'adminpanel/category_list.html')

def view_category(request):
    return render(request, 'adminpanel/view_category.html')

def add_product(request):
    return render(request, 'adminpanel/add_product.html')

def product_list(request):
    return render(request, 'adminpanel/product_list.html')

def edit_product(request):
    return render(request, 'adminpanel/edit_product.html')

def view_product(request):
    return render(request, 'adminpanel/view_product.html')