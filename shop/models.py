from django.db import models
from django.contrib.auth.models import User


class Product(models.Model):
    CATEGORY_CHOICES = [
        ('Men', 'Men'),
        ('Women', 'Women'),
        ('Kids', 'Kids'),
    ]

    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField()
    image = models.ImageField(upload_to='products/')
    stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def original_price(self):
        p = float(self.price)
        markup = p * 1.55
        rounded = round(markup / 50.0) * 50 - 1
        return max(rounded, p + 100)

    @property
    def discount_percent(self):
        mrp = self.original_price
        p = float(self.price)
        if mrp > p:
            return int(round(((mrp - p) / mrp) * 100))
        return 0

    @property
    def rating(self):
        ratings = [4.6, 4.3, 4.8, 4.2, 4.5, 4.7, 4.4, 4.9]
        return ratings[self.id % len(ratings)]

    @property
    def reviews_count(self):
        counts = [1420, 890, 2350, 480, 1690, 720, 3180, 940]
        return counts[self.id % len(counts)]

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    full_name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    pincode = models.CharField(max_length=10, blank=True, default='')

    def __str__(self):
        return self.user.username


class Cart(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField(default=1)

    @property
    def subtotal(self):
        return self.product.price * self.quantity

    def __str__(self):
        return self.user.username + " - " + self.product.name


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created_at']

    def __str__(self):
        return self.user.username + " - " + self.product.name


class Order(models.Model):
    STATUS_CHOICES = [
        ('Placed', 'Order Placed'),
        ('Confirmed', 'Confirmed'),
        ('Shipped', 'Shipped'),
        ('Out for Delivery', 'Out for Delivery'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]

    # Steps shown on the tracking timeline (Cancelled is handled separately)
    TRACK_STEPS = ['Placed', 'Confirmed', 'Shipped', 'Out for Delivery', 'Delivered']

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, default='COD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Placed')
    created_at = models.DateTimeField(auto_now_add=True)

    # Shipping details
    shipping_name = models.CharField(max_length=100, blank=True, default='')
    shipping_email = models.CharField(max_length=150, blank=True, default='')
    shipping_phone = models.CharField(max_length=20, blank=True, default='')
    shipping_address = models.TextField(blank=True, default='')
    shipping_city = models.CharField(max_length=100, blank=True, default='')
    shipping_pincode = models.CharField(max_length=10, blank=True, default='')
    transaction_id = models.CharField(max_length=100, blank=True, default='')

    class Meta:
        ordering = ['-created_at']

    @property
    def order_number(self):
        return "FH" + str(self.id).zfill(6)

    @property
    def payment_label(self):
        return {'COD': 'Cash on Delivery', 'UPI': 'UPI Payment',
                'CARD': 'Card Payment'}.get(self.payment_method, self.payment_method)

    @property
    def tracking_steps(self):
        """List of dicts: label, done, current - used by the tracking timeline."""
        if self.status == 'Cancelled':
            return []
        current = self.TRACK_STEPS.index(self.status)
        labels = {'Placed': 'Order Placed', 'Confirmed': 'Confirmed',
                  'Shipped': 'Shipped', 'Out for Delivery': 'Out for Delivery',
                  'Delivered': 'Delivered'}
        return [{
            'label': labels[name],
            'done': i <= current,
            'current': i == current,
        } for i, name in enumerate(self.TRACK_STEPS)]

    def get_auto_status(self):
        """
        Automatically advances order status over time without manual clicking:
        - 0 to 1 min: Placed
        - 1 to 3 mins: Confirmed
        - 3 to 6 mins: Shipped
        - 6 to 10 mins: Out for Delivery
        - 10+ mins: Delivered
        """
        if self.status == 'Cancelled':
            return 'Cancelled'
        from django.utils import timezone
        elapsed = (timezone.now() - self.created_at).total_seconds()
        if elapsed < 60:
            return 'Placed'
        elif elapsed < 180:
            return 'Confirmed'
        elif elapsed < 360:
            return 'Shipped'
        elif elapsed < 600:
            return 'Out for Delivery'
        else:
            return 'Delivered'

    def update_auto_status(self):
        new_status = self.get_auto_status()
        if self.status != 'Cancelled' and self.status != new_status:
            self.status = new_status
            self.save(update_fields=['status'])
        return self.status

    def __str__(self):
        return self.order_number


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    image = models.CharField(max_length=255, blank=True)

    @property
    def subtotal(self):
        return self.price * self.quantity

    def __str__(self):
        return self.name + " x " + str(self.quantity)


class Review(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(default=5)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.rating}★)"

