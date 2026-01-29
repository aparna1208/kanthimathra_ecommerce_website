from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from typing import Callable
from django.utils.text import slugify
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
import secrets
from django.conf import settings
import random
from decimal import Decimal, ROUND_HALF_UP

def otp_expiry_time():
    return timezone.now() + timezone.timedelta(minutes=2)

class Category(models.Model):
    category_name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=191, unique=True, blank=True)
    short_description = models.CharField(max_length=500, blank=True, null=True)
    thumbnail = models.ImageField(upload_to='category_thumbnail/', blank=True, null=True)
    category_image = models.ImageField(upload_to='category_images/', blank=True, null=True)
    # SEO Fields
    # page_title = models.CharField(max_length=60, blank=True, null=True, help_text="SEO page title (60 chars max)")
    # meta_description = models.CharField(max_length=160, blank=True, null=True, help_text="SEO meta description (160 chars max)")
    # meta_keywords = models.CharField(max_length=160, blank=True, null=True, help_text="SEO meta keywords separated by commas")
    # canonical_tag = models.URLField(blank=True, null=True, help_text="Canonical URL for this page")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Categories'
    
    def __str__(self):
        return self.category_name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.category_name)[:185]
            slug = base
            counter = 0
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                counter += 1
                slug = f"{base}-{counter}"[:191]
            self.slug = slug
        super().save(*args, **kwargs)


class SubCategory(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='subcategories'
    )
    sub_category_name = models.CharField(max_length=100)
    sub_category_image = models.ImageField(upload_to='subcategories/')
    slug = models.SlugField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['category', 'sub_category_name'],
                name='unique_subcategory_per_category'
            )
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.sub_category_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category.category_name} → {self.sub_category_name}"


class Product(models.Model):
    STOCK_CHOICES = (
        ('instock', 'In Stock'),
        ('outofstock', 'Out of Stock'),
    )
    
    product_name = models.CharField(max_length=300)
    slug = models.SlugField(max_length=191, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
      # ✅ ADD THIS
    subcategory = models.ForeignKey(SubCategory,on_delete=models.CASCADE,related_name='products',null=True,blank=True)  # New field for SubCategory
    thumbnail = models.ImageField(upload_to='product_thumbnail/')
    quantity = models.CharField(max_length=50, blank=True, null=True)
    stock = models.CharField(max_length=15, choices=STOCK_CHOICES, default='instock')
    count = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    brand = models.CharField(max_length=255, default="Kanthimantra")
    # SEO Fields
    page_title = models.CharField(max_length=60, blank=True, null=True, help_text="SEO page title (60 chars max)")
    meta_description = models.CharField(max_length=160, blank=True, null=True, help_text="SEO meta description (160 chars max)")
    meta_keywords = models.CharField(max_length=160, blank=True, null=True, help_text="SEO meta keywords separated by commas")
    canonical_tag = models.URLField(blank=True, null=True, help_text="Canonical URL for this page")

    original_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    discount_percentage = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)], default=0)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    product_highlight = models.CharField(max_length=1000, blank=True, help_text="Enter highlights separated by commas (max 5-6 points)")
    description = models.TextField(max_length=300,blank=True, null=True)
    how_to_use = models.TextField(max_length=100,blank=True, null=True)
    shelf_life = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def offer_price_rounded(self):
        return self.offer_price.quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP
        )
    
    
    @property
    def original_price_rounded(self):
        return self.original_price.quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP
        )
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.product_name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.product_name)[:185]
            slug = base
            counter = 0
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                counter += 1
                slug = f"{base}-{counter}"[:191]
            self.slug = slug

        super().save(*args, **kwargs)  # ✅ THIS LINE WAS MISSING

        

class ProductImage(models.Model):
    """Model to store multiple images/videos for each product (up to 5)"""
    MEDIA_TYPE_CHOICES = (
        ('image', 'Image'),
        ('video', 'Video'),
    )
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='media_files')
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, default='image')
    media_file = models.FileField(upload_to='product_media/')
    alt_text = models.CharField(max_length=200, blank=True, null=True)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['display_order']
        constraints = [
            models.UniqueConstraint(fields=['product'], name='max_5_media_files',
                                  condition=models.Q(media_file__isnull=False))
        ]
    
    def __str__(self):
        return f"{self.product.product_name} - {self.media_type}"


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(email, password, **extra_fields)


class Account(models.Model):
    """Custom Account model for users"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE, related_name='account')
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.user.email


class AdminProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="admin_profile")
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True)
    profile_image = models.ImageField(upload_to="admin_profiles/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Admin Profile - {self.user.email}"


class EmailOTP(models.Model):
    email = models.EmailField(max_length=191, db_index=True)
    otp = models.CharField(max_length=6)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,null=True,blank=True,related_name='email_otps')
    is_verified = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=otp_expiry_time)
    purpose = models.CharField(
        max_length=20,
        choices=[
            ("register", "Register"),
            ("reset", "Reset Password")
        ],
        default="register"
    )


    def save(self, *args, **kwargs):
        if not self.pk and not self.otp:  #  only on create
            self.otp = str(random.randint(100000, 999999))
        super().save(*args, **kwargs)

    
    def is_expired(self):
        return timezone.now() > self.expires_at

    def mark_verified(self):
        self.is_verified = True
        self.save()


class PendingRegistration(models.Model):
    email = models.EmailField(max_length=191, unique=True)
    password_hash = models.CharField(max_length=255)
    otp = models.ForeignKey(EmailOTP, on_delete=models.CASCADE, related_name='pending_regs')
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)
        self.save()
        


class ReviewRating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    subject = models.CharField(max_length=100, blank=True)
    review = models.TextField(max_length=500, blank=True)
    rating = models.FloatField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    ip = models.CharField(max_length=20, blank=True)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Review by {self.user.user.first_name} for {self.product.product_name}"



#--------wishlist and cart models --------- (14_01_2026)rdev
class Wishlist(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')



class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart - {self.user}"


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    # NEW: product variant (copied from Product.quantity)
    quantity = models.CharField(max_length=50)

    # RENAMED: number of items user wants
    count = models.PositiveIntegerField(default=1)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    thumbnail = models.ImageField(
        upload_to="cart_thumbnails/",
        blank=True,
        null=True
    )

    class Meta:
        unique_together = ("cart", "product", "quantity")

    @property
    def subtotal(self):
        return self.count * self.price

#-----------cart models --------------

class Order(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders"
    )

    order_id = models.CharField(max_length=50, unique=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    payment_id = models.CharField(max_length=100, blank=True, null=True)
    payment_status = models.BooleanField(default=False)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)

    razorpay_order_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True
    )

    @property
    def subtotal_rounded(self):
        return self.subtotal.quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )

    @property
    def discount_rounded(self):
        return self.discount.quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )

    @property
    def shipping_charge_rounded(self):
        return self.shipping_charge.quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )

    @property
    def total_amount_rounded(self):
        return self.total_amount.quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )

    def __str__(self):
        return f"Order {self.order_id}"
    
class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey("Product", on_delete=models.CASCADE)

    quantity_variant = models.CharField(max_length=50)
    count = models.PositiveIntegerField()

    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def price_rounded(self):
        return self.price.quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )

    @property
    def original_price_rounded(self):
        return self.original_price.quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )

    @property
    def subtotal_rounded(self):
        return (self.price * self.count).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )

    

    def subtotal(self):
        return self.price * self.count
 
    
class ShippingAddress(models.Model):
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="shipping"
    )

    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)

    address = models.TextField()
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    pincode = models.CharField(max_length=10)
    country = models.CharField(max_length=50, default="India")

    # landmark / delivery instructions
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.full_name
    


# CMS Models ------------------------#


class HomeSlider(models.Model):
    image = models.ImageField(upload_to="cms/home/sliders/")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Home Slider {self.id}"


class HomeCenterBanner(models.Model):
    banner1 = models.ImageField(upload_to="cms/home/center_banner/", blank=True, null=True)
    banner2 = models.ImageField(upload_to="cms/home/center_banner/", blank=True, null=True)
    banner3 = models.ImageField(upload_to="cms/home/center_banner/", blank=True, null=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Home Center Banner"


class HomeVideo(models.Model):
    VIDEO_TYPE_CHOICES = (
        ("upload", "Upload"),
        ("youtube", "Youtube"),
    )

    video_type = models.CharField(max_length=20, choices=VIDEO_TYPE_CHOICES, default="upload")
    video_file = models.FileField(upload_to="cms/home/video/", blank=True, null=True)
    youtube_url = models.URLField(blank=True, null=True)
    youtube_id = models.CharField(max_length=50, blank=True, null=True)

    thumbnail = models.ImageField(upload_to="cms/home/video_thumbnails/", blank=True, null=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Home Video ({self.video_type})"


class HomeEndBanner(models.Model):
    image = models.ImageField(upload_to="cms/home/end_banners/")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"End Banner {self.id}"


class HomeFlashNews(models.Model):
    text = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text[:40]

