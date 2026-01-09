from django.urls import path,reverse_lazy
from . import views

app_name = 'web' 

urlpatterns = [ 
    
    #----WEB FRONTEND URLS----#
    path('', views.index, name='index'),



    #----ADMIN PANEL URLS----#
    path('adminpanel/', views.admin_dashboard, name='admin_dashboard'),


    path('adminpanel/category/add/', views.add_category, name='add_category'),
    path('adminpanel/all_categories/', views.category_list, name='category_list'),
    path('adminpanel/view_category/', views.view_category, name='view_category'),
    path('adminpanel/product/add/', views.add_product, name='add_product'),
    path('adminpanel/all_products/', views.product_list, name='product_list'),
    path('adminpanel/edit_product/', views.edit_product, name='edit_product'),
    path('adminpanel/view_product/', views.view_product, name='view_product'),


]