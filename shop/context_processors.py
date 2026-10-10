from .models import Cart, Wishlist


def shop_counts(request):
    """Gives every template: cart_count, wishlist_count, wishlist_ids."""
    if request.user.is_authenticated:
        cart_count = sum(Cart.objects.filter(user=request.user).values_list("quantity", flat=True))
        wishlist_ids = list(Wishlist.objects.filter(user=request.user).values_list("product_id", flat=True))
        return {
            "cart_count": cart_count,
            "wishlist_count": len(wishlist_ids),
            "wishlist_ids": wishlist_ids,
        }
    return {"cart_count": 0, "wishlist_count": 0, "wishlist_ids": []}
