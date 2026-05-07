# from django.urls import path
# from . import views

# urlpatterns = [
#     # Home
#     path('', views.home, name='home'),

#     # Restaurants
#     path('restaurants/', views.restaurant_list, name='restaurant_list'),
#     path('restaurant/<int:pk>/', views.restaurant_detail, name='restaurant_detail'),

#     # Cart
#     path('cart/', views.cart_view, name='cart'),
#     path('cart/add/<int:food_id>/', views.add_to_cart, name='add_to_cart'),
#     path('cart/remove/<int:cart_id>/', views.remove_from_cart, name='remove_from_cart'),
#     path('cart/update/<int:cart_id>/', views.update_cart, name='update_cart'),

#     # Orders
#     path('checkout/', views.checkout, name='checkout'),
#     path('orders/', views.order_list, name='order_list'),
#     path('order/<int:pk>/', views.order_detail, name='order_detail'),

#     # Auth
#     path('search-suggestions/', views.search_suggestions, name='search_suggestions'),

#     path('register/', views.register_view, name='register'),
#     path('login/', views.login_view, name='login'),
#     path('logout/', views.logout_view, name='logout'),

#     # Store / Menu
#     path('store/', views.store, name='store'),
#     path('store/category/<int:category_id>/', views.store, name='store_by_category'),
# ]


from django.urls import path
from . import views

urlpatterns = [
    # Home
    path('', views.home, name='home'),

    # Restaurants
    path('restaurants/', views.restaurant_list, name='restaurant_list'),
    path('restaurant/<int:pk>/', views.restaurant_detail, name='restaurant_detail'),

    # Cart
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:food_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:cart_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:cart_id>/', views.update_cart, name='update_cart'),

    # Orders
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_list, name='order_list'),
    path('order/<int:pk>/', views.order_detail, name='order_detail'),

    # Auth
    path('search-suggestions/', views.search_suggestions, name='search_suggestions'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Store / Menu
    path('store/', views.store, name='store'),
    path('store/category/<int:category_id>/', views.store, name='store_by_category'),
]


# from django.contrib import admin
# from .models import Restaurant, Category, FoodItem, Cart, Order, OrderItem

# @admin.register(Restaurant)
# class RestaurantAdmin(admin.ModelAdmin):
#     list_display = ['name', 'address', 'delivery_time', 'is_open']
#     list_filter = ['is_open']
#     search_fields = ['name', 'description']

# @admin.register(Category)
# class CategoryAdmin(admin.ModelAdmin):
#     list_display = ['name', 'restaurant']
#     list_filter = ['restaurant']
#     search_fields = ['name']

# @admin.register(FoodItem)
# class FoodItemAdmin(admin.ModelAdmin):
#     list_display = ['name', 'category', 'price_single', 'price_small', 'price_medium', 'is_available']
#     list_filter = ['category', 'is_available']
#     search_fields = ['name', 'description']

# @admin.register(Cart)
# class CartAdmin(admin.ModelAdmin):
#     list_display = ['user', 'food_item', 'quantity', 'selected_size']
#     list_filter = ['selected_size']

# @admin.register(Order)
# class OrderAdmin(admin.ModelAdmin):
#     list_display = ['id', 'user', 'created_at', 'status', 'total_amount']
#     list_filter = ['status', 'created_at']
#     search_fields = ['user__username', 'address']

# @admin.register(OrderItem)
# class OrderItemAdmin(admin.ModelAdmin):
#     list_display = ['order', 'food_item', 'quantity', 'selected_size', 'price']