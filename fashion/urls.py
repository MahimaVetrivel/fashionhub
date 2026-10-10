from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from shop import views


urlpatterns = [

    path('admin/', admin.site.urls),

    path('', views.home, name='home'),
    path('search/', views.search_products, name='search'),
    path('api/search-suggest/', views.search_suggest, name='search_suggest'),

    path('login/', views.login_page, name='login'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/', views.reset_password, name='reset_password'),

    path('register/', views.register_page, name='register'),

    path('verify-otp/', views.verify_otp, name='verify_otp'),

    path('logout/', views.logout_page, name='logout'),

    path(
        'category/<str:category_name>/',
        views.category_page,
        name='category'
    ),

    path('profile/', views.my_profile, name='my_profile'),

    path(
        'product/<int:id>/',
        views.product_detail,
        name='product_detail'
    ),

    path(
        'add-to-cart/<int:id>/',
        views.add_to_cart,
        name='add_to_cart'
    ),

    path(
        'cart/',
        views.cart,
        name='cart'
    ),

    path(
        'checkout/',
        views.checkout_page,
        name='checkout'
    ),

    path(
        'order-success/',
        views.order_success,
        name='order_success'
    ),

    path('cart/update/<int:id>/<str:action>/', views.update_cart, name='update_cart'),

    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/toggle/<int:id>/', views.toggle_wishlist, name='toggle_wishlist'),
    path('wishlist/move-to-cart/<int:id>/', views.move_to_cart, name='move_to_cart'),

    path('product/<int:id>/review/', views.add_review, name='add_review'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('my-orders/<int:id>/', views.track_order, name='track_order'),
    path('my-orders/<int:id>/status-api/', views.order_status_api, name='order_status_api'),
    path('my-orders/<int:id>/advance-status/', views.advance_order_status, name='advance_order_status'),
    path('my-orders/<int:id>/resend-email/', views.resend_order_email, name='resend_order_email'),
    path('my-orders/<int:id>/cancel/', views.cancel_order, name='cancel_order'),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )