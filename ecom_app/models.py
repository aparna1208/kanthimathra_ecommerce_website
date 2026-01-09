from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from typing import Callable
from django.utils.text import slugify
import secrets


def otp_expiry_time():
    return timezone.now() + timezone.timedelta(minutes=3)

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


class Product(models.Model):
    STOCK_CHOICES = (
        ('instock', 'In Stock'),
        ('outofstock', 'Out of Stock'),
    )
    
    product_name = models.CharField(max_length=300)
    slug = models.SlugField(max_length=191, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    thumbnail = models.ImageField(upload_to='product_thumbnail/')
    quantity = models.IntegerField(validators=[MinValueValidator(0)])
    stock = models.CharField(max_length=15, choices=STOCK_CHOICES, default='instock')
    # SEO Fields
    page_title = models.CharField(max_length=60, blank=True, null=True, help_text="SEO page title (60 chars max)")
    meta_description = models.CharField(max_length=160, blank=True, null=True, help_text="SEO meta description (160 chars max)")
    meta_keywords = models.CharField(max_length=160, blank=True, null=True, help_text="SEO meta keywords separated by commas")
    canonical_tag = models.URLField(blank=True, null=True, help_text="Canonical URL for this page")

    original_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    discount_percentage = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)], default=0)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    product_highlight = models.CharField(max_length=1000, blank=True, help_text="Enter highlights separated by commas (max 5-6 points)")
    description = models.TextField(blank=True, null=True)
    how_to_use = models.TextField(blank=True, null=True)
    shelf_life = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.product_name
    
    def save(self, *args, **kwargs):
        # generate unique slug if not set
        if not self.slug:
            base = slugify(self.product_name)[:185]
            slug = base
            counter = 0
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                counter += 1
                slug = f"{base}-{counter}"[:191]
            self.slug = slug
        
        # Calculate offer_price based on discount_percentage
        if self.discount_percentage > 0:
            discount_amount = (self.original_price * self.discount_percentage) / 100
            self.offer_price = self.original_price - discount_amount
        else:
            self.offer_price = self.original_price
        super().save(*args, **kwargs)


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


class Account(models.Model):
    """Custom Account model for users"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='account')
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


class EmailOTP(models.Model):
    email = models.EmailField(max_length=191, db_index=True)
    otp = models.CharField(max_length=6)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='email_otps')
    is_verified = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=otp_expiry_time)

    class Meta:
        ordering = ['-created_at']
    
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
