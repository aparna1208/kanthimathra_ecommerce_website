from django.urls import path,reverse_lazy
from . import views

app_name = 'web' 

urlpatterns = [ 
    
    #----WEB FRONTEND URLS----#
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
   
    path('shop/', views.shop, name='shop'),
    path('account/', views.account, name='account'),
    path('account-settings/', views.account_settings, name='account_settings'),
    path('account-orders/', views.order_history, name='account_orders'),
    path('order-history/', views.order_history, name='order_history'),
    path('account-address/', views.address, name='account_address'),
    path('account-redirect/', views.account_redirect, name='account_redirect'),
    path('product_detail/<slug:slug>/', views.product_detail, name='product_detail'),

    # path('address/', views.address, name='address'),
    path('blog/', views.blog, name='blog'),
    path('blog_single/', views.blog_single, name='blog_single'),
    path('contact/', views.contact, name='contact'),
    path('login/', views.login_view, name='login'),
    path("verify-otp/", views.verify_otp_view, name="verify_otp"),
    path("resend-otp/", views.resend_otp_view, name="resend_otp"), #----------14_01-------
    path('register/', views.register_view, name='register'),
    path("logout/", views.logout_view, name="logout"),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path("verify-reset-otp/", views.verify_reset_otp_view, name="verify_reset_otp"),
    path('reset-password/', views.reset_password_view, name='reset_password'),
    path("wishlist/", views.wishlist, name="wishlist"),
    path("wishlist/toggle/", views.toggle_wishlist, name="toggle_wishlist"),

    # ---------- CART ----------
    path("cart/", views.cart, name="cart"),
    path("cart/add/", views.add_to_cart_view, name="add_to_cart"),
    path("cart/update/", views.update_cart_item, name="update_cart_item"),
    path("cart/remove/", views.remove_cart_item, name="remove_cart_item"),
    path('checkout/', views.checkout, name='checkout'),
    path("payment/<int:order_id>/", views.payment, name="payment"), 
 
    path("payment-success/", views.payment_success, name="payment_success"),
    path("order-success/<int:order_id>/", views.order_success, name="order_success"),
    path("invoice/<int:order_id>/", views.invoice_view, name="invoice_view"),
    path("invoice/pdf/<int:order_id>/", views.generate_invoice, name="generate_invoice"),
    path("buy-now/", views.buy_now, name="buy_now"),

    path('category/', views.category, name='category'),
    path("category/<int:cat_id>/", views.category_single, name="category_single"),

    path("gallery/", views.gallery, name="gallery"),
    path("terms_and_conditions/", views.terms_and_conditions, name="terms_and_conditions"),
    path("privacy_policy/", views.privacy_policy, name="privacy_policy"),

    #----ADMIN PANEL URLS----#
    # path('adminpanel/login/', views.admin_login, name='admin_login'),
    path('adminpanel/', views.admin_login, name='admin_login'),
    path('adminpanel/logout/', views.admin_logout, name='admin_logout'), 

    path('adminpanel/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('adminpanel/settings/', views.admin_settings, name='admin_settings'),

    # category URLs
    path('adminpanel/category/add/', views.add_category, name='add_category'),
    path('adminpanel/category/list/', views.category_list, name='category_list'),
    path('adminpanel/category/<int:category_id>/edit/', views.edit_category, name='edit_category'),
    path('adminpanel/category/<int:category_id>/delete/', views.delete_category, name='delete_category'),
    path('adminpanel/category/<int:category_id>/view/', views.view_category, name='view_category'),

    # subcategory URLs
    path('adminpanel/subcategory/add/', views.sub_category_add, name='add_sub_category'),
    path('adminpanel/subcategory/list/', views.sub_category_list, name='sub_category_list'),
    path('adminpanel/subcategory/view/<int:id>/', views.sub_category_view, name='view_sub_category'),
    path('adminpanel/subcategory/edit/<int:id>/',views.sub_category_edit,name='edit_sub_category'),
    path('adminpanel/subcategory/delete/<int:id>/',views.sub_category_delete,name='delete_sub_category'),


    # product URLs
    path('adminpanel/product/add/', views.add_product, name='add_product'),
    path('adminpanel/product/list/', views.product_list, name='product_list'),
    
    path('adminpanel/product/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('adminpanel/product/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    path('adminpanel/product/<int:product_id>/view/', views.view_product, name='view_product'),

    path('adminpanel/order_list/', views.order_list, name='order_list'),
    path('adminpanel/order/<int:order_id>/detail/', views.order_detail, name='order_detail'),
    path("adminpanel/orders/delete/<int:order_id>/",views.order_delete,name="adminpanel_order_delete"),

    path('adminpanel/users/', views.all_users, name='all_users'),
    path('adminpanel/user/<int:user_id>/view/', views.view_user, name='view_user'),
    path('adminpanel/users/delete/<int:user_id>/', views.admin_delete_user, name='admin_delete_user'),

    # cms
    path('adminpanel/cms_home/', views.cms_home, name='cms_home'),
    path('adminpanel/cms_home/slider/delete/<int:pk>/', views.delete_slider, name='delete_slider'),
    path("adminpanel/cms_home/endbanner/delete/<int:pk>/", views.delete_end_banner, name="delete_end_banner"),
    path('adminpanel/cms_contact/', views.cms_contact, name='cms_contact'),
    path('adminpanel/cms_legal/', views.cms_legal, name='cms_legal'),
    path('adminpanel/cms_blogs/', views.cms_blogs, name='cms_blogs'),
 ]