from django.contrib import admin
from .models import Product, Cart, Wishlist, Order, OrderItem

admin.site.register(Product)
admin.site.register(Cart)
admin.site.register(Wishlist)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'total', 'payment_method', 'status', 'created_at')
    list_editable = ('status',)          # change tracking status right from the list
    list_filter = ('status', 'payment_method')
    inlines = [OrderItemInline]
