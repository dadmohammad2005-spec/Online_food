from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from .models import Restaurant, Category, FoodItem, Cart, Order, OrderItem


def home(request):
    restaurants = Restaurant.objects.filter(is_open=True)
    query = request.GET.get('q')
    if query:
        restaurants = restaurants.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    return render(request, 'food/home.html', {
        'restaurants': restaurants,
        'query': query
    })


def restaurant_list(request):
    restaurants = Restaurant.objects.filter(is_open=True)
    return render(request, 'food/restaurant_list.html', {'restaurants': restaurants})


def restaurant_detail(request, pk):
    restaurant = get_object_or_404(Restaurant, pk=pk)
    categories = restaurant.categories.prefetch_related('items').all()
    return render(request, 'food/restaurant_detail.html', {
        'restaurant': restaurant,
        'categories': categories,
    })


# ── LIVE SEARCH ──────────────────────────────────────────
def search_suggestions(request):
    query = request.GET.get('q', '')
    results = []

    if len(query) >= 2:
        # Restaurants
        restaurants = Restaurant.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )[:4]
        for r in restaurants:
            results.append({
                'type': 'restaurant',
                'name': r.name,
                'subtitle': f'🕒 {r.delivery_time}  |  📍 {r.address}',
                'price': f'Delivery: Rs. {r.delivery_charge}',
                'url': f'/restaurant/{r.pk}/',
                'open': r.is_open,
            })

        # Food items with prices
        food_items = FoodItem.objects.filter(
            Q(name__icontains=query),
            is_available=True
        ).select_related('category__restaurant')[:6]

        for item in food_items:
            # Build size price string
            sizes = []
            if item.price_single:
                sizes.append(f'Single: Rs.{item.price_single}')
            if item.price_small:
                sizes.append(f'Small: Rs.{item.price_small}')
            if item.price_medium:
                sizes.append(f'Medium: Rs.{item.price_medium}')
            if item.price_large:
                sizes.append(f'Large: Rs.{item.price_large}')
            if item.price_family:
                sizes.append(f'Family: Rs.{item.price_family}')

            price_str = '  |  '.join(sizes) if sizes else 'Price not set'

            results.append({
                'type': 'food',
                'name': item.name,
                'subtitle': f'📍 {item.category.restaurant.name}',
                'price': price_str,
                'url': f'/restaurant/{item.category.restaurant.pk}/',
                'open': True,
            })

    return JsonResponse({'results': results})


# ── CART ─────────────────────────────────────────────────
@login_required
def cart_view(request):
    cart_items = Cart.objects.filter(user=request.user).select_related('food_item')
    subtotal = sum(item.total_price() for item in cart_items)
    delivery = 50
    total = subtotal + delivery
    return render(request, 'food/cart.html', {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'delivery': delivery,
        'total': total,
    })


@login_required
def add_to_cart(request, food_id):
    food_item = get_object_or_404(FoodItem, id=food_id)

    if request.method == 'POST':
        selected_size = request.POST.get('size', 'single')
        # Get price for selected size
        price_map = {
            'single': food_item.price_single,
            'small': food_item.price_small,
            'medium': food_item.price_medium,
            'large': food_item.price_large,
            'family': food_item.price_family,
        }
        selected_price = price_map.get(selected_size) or food_item.get_min_price()

        cart_item, created = Cart.objects.get_or_create(
            user=request.user,
            food_item=food_item,
            selected_size=selected_size,
            defaults={'selected_price': selected_price}
        )
        if not created:
            cart_item.quantity += 1
            cart_item.save()

        messages.success(request, f'"{food_item.name} ({selected_size})" added to cart!')
    return redirect(request.META.get('HTTP_REFERER', 'cart'))


@login_required
def remove_from_cart(request, cart_id):
    cart_item = get_object_or_404(Cart, id=cart_id, user=request.user)
    cart_item.delete()
    messages.success(request, 'Item removed from cart.')
    return redirect('cart')


@login_required
def update_cart(request, cart_id):
    cart_item = get_object_or_404(Cart, id=cart_id, user=request.user)
    quantity = int(request.POST.get('quantity', 1))
    if quantity > 0:
        cart_item.quantity = quantity
        cart_item.save()
    else:
        cart_item.delete()
    return redirect('cart')


# ── CHECKOUT ─────────────────────────────────────────────
@login_required
def checkout(request):
    cart_items = Cart.objects.filter(user=request.user).select_related('food_item')
    subtotal = sum(item.total_price() for item in cart_items)
    delivery_charge = 50
    total = subtotal + delivery_charge

    if not cart_items:
        messages.error(request, 'Your cart is empty!')
        return redirect('cart')

    if request.method == 'POST':
        address = request.POST.get('address')
        order = Order.objects.create(
            user=request.user,
            total_amount=subtotal,
            delivery_charge=delivery_charge,
            address=address,
            status='pending'
        )
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                food_item=item.food_item,
                quantity=item.quantity,
                selected_size=item.selected_size,
                price=item.selected_price
            )
        cart_items.delete()
        messages.success(request, f'Order #{order.id} placed successfully! 🎉')
        return redirect('order_detail', pk=order.id)

    return render(request, 'food/checkout.html', {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'delivery_charge': delivery_charge,
        'total': total,
    })


# ── ORDERS ───────────────────────────────────────────────
@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'food/order_list.html', {'orders': orders})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, 'food/order_detail.html', {'order': order})


# ── AUTH ─────────────────────────────────────────────────
def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        if password1 != password2:
            messages.error(request, 'Passwords do not match!')
            return redirect('register')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken!')
            return redirect('register')
        user = User.objects.create_user(username=username, email=email, password=password1)
        login(request, user)
        messages.success(request, f'Welcome {username}! 🎉')
        return redirect('home')
    return render(request, 'food/register.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, f'Welcome back, {username}! 👋')
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password!')
    return render(request, 'food/login.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('home')