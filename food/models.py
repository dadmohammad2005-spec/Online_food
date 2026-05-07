from django.db import models
from django.contrib.auth.models import User

# Restaurant Model
class Restaurant(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='restaurants/')
    address = models.CharField(max_length=300)
    delivery_time = models.CharField(max_length=50)  # e.g "30-40 min"
    delivery_charge = models.DecimalField(max_digits=6, decimal_places=2, default=50)
    is_open = models.BooleanField(default=True)

    def __str__(self):
        return self.name


# Category Model (Burgers, Pizza, Drinks etc)
class Category(models.Model):
    name = models.CharField(max_length=100)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='categories')

    def __str__(self):
        return f"{self.restaurant.name} - {self.name}"


# Food Item Model (Simplified with single price)
class FoodItem(models.Model):
    SIZE_CHOICES = [
        ('single', 'Single'),
        ('small', 'Small'),
        ('medium', 'Medium'),
        ('large', 'Large'),
        ('family', 'Family'),
    ]

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=200)
    description = models.TextField()
    size = models.CharField(max_length=10, choices=SIZE_CHOICES, default='single')
    
    # Price for each size (null means size not available)
    price_single = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    price_small = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    price_medium = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    price_large = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    price_family = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    image = models.ImageField(upload_to='food_items/', blank=True, null=True)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        size_info = f" ({self.get_size_display()})" if self.has_sizes() else ""
        return f"{self.name}{size_info}"

    def get_current_price(self):
        """Get price based on selected size"""
        price_map = {
            'single': self.price_single,
            'small': self.price_small,
            'medium': self.price_medium,
            'large': self.price_large,
            'family': self.price_family,
        }
        return price_map.get(self.size, self.price_single)

    def get_min_price(self):
        prices = [p for p in [
            self.price_single, self.price_small,
            self.price_medium, self.price_large, self.price_family
        ] if p is not None]
        return min(prices) if prices else 0

    def get_max_price(self):
        prices = [p for p in [
            self.price_single, self.price_small,
            self.price_medium, self.price_large, self.price_family
        ] if p is not None]
        return max(prices) if prices else 0

    def has_sizes(self):
        """Check if item has multiple size options"""
        return any([self.price_small, self.price_medium, self.price_large, self.price_family])

    def available_sizes(self):
        """Return list of available sizes with their prices"""
        sizes = []
        size_mapping = {
            'single': self.price_single,
            'small': self.price_small,
            'medium': self.price_medium,
            'large': self.price_large,
            'family': self.price_family,
        }
        for size, price in size_mapping.items():
            if price is not None:
                sizes.append({'size': size, 'price': price})
        return sizes


# Cart Model
class Cart(models.Model):
    SIZE_CHOICES = [
        ('single', 'Single'),
        ('small', 'Small'),
        ('medium', 'Medium'),
        ('large', 'Large'),
        ('family', 'Family'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    selected_size = models.CharField(max_length=10, choices=SIZE_CHOICES, default='single')
    selected_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    class Meta:
        unique_together = ['user', 'food_item', 'selected_size']  # Prevent duplicate cart items

    def __str__(self):
        return f"{self.user.username} - {self.food_item.name} ({self.selected_size})"

    def save(self, *args, **kwargs):
        # Auto-calculate price based on selected size
        if not self.selected_price:
            price_map = {
                'single': self.food_item.price_single,
                'small': self.food_item.price_small,
                'medium': self.food_item.price_medium,
                'large': self.food_item.price_large,
                'family': self.food_item.price_family,
            }
            self.selected_price = price_map.get(self.selected_size, 0)
        super().save(*args, **kwargs)

    def total_price(self):
        return self.quantity * self.selected_price


# Order Model
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('on_the_way', 'On The Way'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_charge = models.DecimalField(max_digits=6, decimal_places=2, default=50)
    address = models.TextField()
    
    # Optional: Add restaurant reference
    restaurant = models.ForeignKey(Restaurant, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

    def grand_total(self):
        return self.total_amount + self.delivery_charge


# Order Item Model
class OrderItem(models.Model):
    SIZE_CHOICES = [
        ('single', 'Single'),
        ('small', 'Small'),
        ('medium', 'Medium'),
        ('large', 'Large'),
        ('family', 'Family'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    selected_size = models.CharField(max_length=10, choices=SIZE_CHOICES, default='single')
    price = models.DecimalField(max_digits=8, decimal_places=2)  # Price at time of order

    def __str__(self):
        return f"{self.food_item.name} ({self.selected_size}) x{self.quantity}"

    def subtotal(self):
        return self.quantity * self.price