from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Sum, F
from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import Restaurant, Category, FoodItem, Cart, Order, OrderItem
import json

# ─── SEARCH SUGGESTIONS (LIVE SEARCH) ───────────────────
def search_suggestions(request):
    query = request.GET.get('q', '')
    results = []

    if query and len(query) >= 2:
        # Search restaurants
        restaurants = Restaurant.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query),
            is_open=True
        )[:3]
        
        for r in restaurants:
            results.append({
                'type': 'restaurant',
                'name': r.name,
                'subtitle': f"📍 {r.address[:50]} • 🕒 {r.delivery_time}",
                'url': f'/restaurant/{r.pk}/'
            })

        # Search food items (with multiple sizes support)
        food_items = FoodItem.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query),
            is_available=True
        ).select_related('category__restaurant')[:5]
        
        for item in food_items:
            min_price = item.get_min_price()
            max_price = item.get_max_price()
            price_text = f"Rs. {min_price}"
            if min_price != max_price:
                price_text = f"Rs. {min_price} - {max_price}"
            
            results.append({
                'type': 'food',
                'name': item.name,
                'subtitle': f"{price_text} — {item.category.restaurant.name}",
                'url': f'/restaurant/{item.category.restaurant.pk}/#item-{item.pk}'
            })

    return JsonResponse({'results': results})


# ─── HOME ───────────────────────────────────────────────
def home(request):
    restaurants = Restaurant.objects.filter(is_open=True)
    query = request.GET.get('q', '')
    
    if query:
        # Search across restaurants and their food items
        restaurants = restaurants.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(categories__items__name__icontains=query)
        ).distinct()
    
    # Add pagination
    paginator = Paginator(restaurants, 9)  # 9 restaurants per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get categories for filter bar
    categories = Category.objects.all()[:8]  # Limit to 8 categories
    
    context = {
        'restaurants': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'query': query,
        'categories': categories,
        'total_restaurants': Restaurant.objects.filter(is_open=True).count(),
        'total_food_items': FoodItem.objects.filter(is_available=True).count(),
    }
    
    return render(request, 'food/home.html', context)


# ─── RESTAURANT LIST ────────────────────────────────────
def restaurant_list(request):
    restaurants = Restaurant.objects.filter(is_open=True)
    query = request.GET.get('q')
    
    if query:
        restaurants = restaurants.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    
    # Pagination
    paginator = Paginator(restaurants, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'food/restaurant_list.html', {
        'restaurants': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'query': query
    })


# ─── RESTAURANT DETAIL ──────────────────────────────────
def restaurant_detail(request, pk):
    restaurant = get_object_or_404(Restaurant, pk=pk, is_open=True)
    categories = restaurant.categories.prefetch_related('items').all()
    
    # Get food items with available sizes info
    for category in categories:
        for item in category.items.all():
            item.available_sizes = item.available_sizes()
            item.has_multiple_sizes = item.has_sizes()
    
    return render(request, 'food/restaurant_detail.html', {
        'restaurant': restaurant,
        'categories': categories,
    })


# ─── STORE / MENU ────────────────────────────────────────
def store(request, category_id=None):
    search_query = request.GET.get('search', '').strip()
    categories = Category.objects.all().order_by('name')
    food_items = FoodItem.objects.filter(is_available=True)
    current_category = None

    if category_id:
        category = get_object_or_404(Category, id=category_id)
        food_items = food_items.filter(category=category)
        current_category = category.id

    if search_query:
        food_items = food_items.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(category__restaurant__name__icontains=search_query)
        ).distinct()
    
    # Add available sizes info
    for item in food_items:
        item.available_sizes = item.available_sizes()
        item.min_price = item.get_min_price()
        item.max_price = item.get_max_price()
    
    # Pagination
    paginator = Paginator(food_items, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'food/store.html', {
        'categories': categories,
        'food_items': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'search_query': search_query,
        'current_category': current_category,
    })


# ─── CART VIEW ──────────────────────────────────────────
@login_required
def cart_view(request):
    cart_items = Cart.objects.filter(user=request.user).select_related('food_item__category__restaurant')
    
    subtotal = sum(item.total_price() for item in cart_items)
    delivery_charge = 50  # Default delivery charge
    total = subtotal + delivery_charge
    
    # Group by restaurant
    cart_by_restaurant = {}
    for item in cart_items:
        restaurant = item.food_item.category.restaurant
        if restaurant not in cart_by_restaurant:
            cart_by_restaurant[restaurant] = []
        cart_by_restaurant[restaurant].append(item)
    
    return render(request, 'food/cart.html', {
        'cart_items': cart_items,
        'cart_by_restaurant': cart_by_restaurant,
        'subtotal': subtotal,
        'delivery_charge': delivery_charge,
        'total': total
    })


# ─── ADD TO CART ────────────────────────────────────────
@login_required
def add_to_cart(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            food_id = data.get('food_id')
            size = data.get('size', 'single')
            quantity = int(data.get('quantity', 1))
            
            food_item = get_object_or_404(FoodItem, id=food_id, is_available=True)
            
            # Get price based on selected size
            price_map = {
                'single': food_item.price_single,
                'small': food_item.price_small,
                'medium': food_item.price_medium,
                'large': food_item.price_large,
                'family': food_item.price_family,
            }
            
            selected_price = price_map.get(size)
            if selected_price is None:
                return JsonResponse({'error': 'Invalid size selected'}, status=400)
            
            # Get or create cart item
            cart_item, created = Cart.objects.get_or_create(
                user=request.user,
                food_item=food_item,
                selected_size=size,
                defaults={
                    'quantity': quantity,
                    'selected_price': selected_price
                }
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
            
            # Get updated cart count
            cart_count = Cart.objects.filter(user=request.user).count()
            
            return JsonResponse({
                'success': True,
                'message': f'"{food_item.name}" ({size}) added to cart!',
                'cart_count': cart_count
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)


# ─── REMOVE FROM CART ───────────────────────────────────
@login_required
def remove_from_cart(request, cart_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(Cart, id=cart_id, user=request.user)
        cart_item.delete()
        messages.success(request, 'Item removed from cart.')
    return redirect('cart')


# ─── UPDATE CART ────────────────────────────────────────
@login_required
def update_cart(request, cart_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(Cart, id=cart_id, user=request.user)
        
        # Handle AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data = json.loads(request.body)
            quantity = int(data.get('quantity', 1))
        else:
            quantity = int(request.POST.get('quantity', 1))
        
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
            new_total = cart_item.total_price()
            
            # Calculate cart totals
            cart_items = Cart.objects.filter(user=request.user)
            subtotal = sum(item.total_price() for item in cart_items)
            delivery_charge = 50
            grand_total = subtotal + delivery_charge
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'new_total': float(new_total),
                    'subtotal': float(subtotal),
                    'grand_total': float(grand_total),
                    'cart_count': cart_items.count()
                })
        else:
            cart_item.delete()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'deleted': True})
        
        messages.success(request, 'Cart updated!')
    
    return redirect('cart')


# ─── CHECKOUT ───────────────────────────────────────────
@login_required
def checkout(request):
    cart_items = Cart.objects.filter(user=request.user).select_related('food_item__category__restaurant')
    
    if not cart_items:
        messages.error(request, 'Your cart is empty!')
        return redirect('cart')
    
    subtotal = sum(item.total_price() for item in cart_items)
    delivery_charge = 50
    total = subtotal + delivery_charge
    
    # Get unique restaurants in cart
    restaurants = set()
    for item in cart_items:
        restaurants.add(item.food_item.category.restaurant)
    
    if len(restaurants) > 1:
        messages.warning(request, f'Your cart has items from {len(restaurants)} different restaurants. Delivery charges will apply separately.')
    
    if request.method == 'POST':
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        notes = request.POST.get('notes', '')
        
        if not address:
            messages.error(request, 'Please provide delivery address!')
            return redirect('checkout')
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            total_amount=subtotal,
            delivery_charge=delivery_charge,
            address=address,
            status='pending'
        )
        
        # Create order items
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                food_item=item.food_item,
                quantity=item.quantity,
                selected_size=item.selected_size,
                price=item.selected_price
            )
        
        # Clear cart
        cart_items.delete()
        
        messages.success(request, f'Order #{order.id} placed successfully! 🎉')
        return redirect('order_detail', pk=order.id)
    
    return render(request, 'food/checkout.html', {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'delivery_charge': delivery_charge,
        'total': total
    })


# ─── ORDER LIST ─────────────────────────────────────────
@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    # Add order summary for each order
    for order in orders:
        order.item_count = order.items.aggregate(total=Sum('quantity'))['total'] or 0
    
    # Pagination
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'food/order_list.html', {
        'orders': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages()
    })


# ─── ORDER DETAIL ───────────────────────────────────────
@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    order_items = order.items.select_related('food_item__category__restaurant').all()
    
    # Group items by restaurant
    items_by_restaurant = {}
    for item in order_items:
        restaurant = item.food_item.category.restaurant
        if restaurant not in items_by_restaurant:
            items_by_restaurant[restaurant] = []
        items_by_restaurant[restaurant].append(item)
    
    return render(request, 'food/order_detail.html', {
        'order': order,
        'order_items': order_items,
        'items_by_restaurant': items_by_restaurant
    })


# ─── REGISTER ───────────────────────────────────────────
def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        # Validation
        if not all([username, email, password1, password2]):
            messages.error(request, 'All fields are required!')
            return redirect('register')

        if password1 != password2:
            messages.error(request, 'Passwords do not match!')
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken!')
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered!')
            return redirect('register')

        # Create user
        user = User.objects.create_user(username=username, email=email, password=password1)
        login(request, user)
        messages.success(request, f'Welcome {username}! Account created successfully 🎉')
        return redirect('home')

    return render(request, 'food/register.html')


# ─── LOGIN ──────────────────────────────────────────────
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if not username or not password:
            messages.error(request, 'Please enter both username and password!')
            return redirect('login')
        
        user = authenticate(request, username=username, password=password)
        
        if user:
            login(request, user)
            messages.success(request, f'Welcome back, {username}! 👋')
            
            # Redirect to next parameter if exists
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password!')

    return render(request, 'food/login.html')


# ─── LOGOUT ─────────────────────────────────────────────
def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('home')