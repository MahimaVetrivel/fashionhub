from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
import random
from django.http import JsonResponse
from django.contrib import messages
from .models import Product, Cart, Profile, Wishlist, Order, OrderItem, Review


from django.db.models import Q


def home(request):
    products = Product.objects.all()
    featured_products = Product.objects.all()[:8]
    trending_women = Product.objects.filter(category='Women')[:4]
    trending_men = Product.objects.filter(category='Men')[:4]
    trending_kids = Product.objects.filter(category='Kids')[:4]

    return render(request, "home.html", {
        "products": products,
        "featured_products": featured_products,
        "trending_women": trending_women,
        "trending_men": trending_men,
        "trending_kids": trending_kids,
    })


# -------------------------
# SEARCH PRODUCTS
# -------------------------

def search_products(request):
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    sort = request.GET.get("sort", "").strip()
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()

    products = Product.objects.all()

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__icontains=query)
        )

    if category and category != "All":
        products = products.filter(category=category)

    if min_price:
        try:
            products = products.filter(price__gte=float(min_price))
        except ValueError:
            pass

    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
        except ValueError:
            pass

    # Sorting
    if sort == "price_asc":
        products = products.order_by("price")
    elif sort == "price_desc":
        products = products.order_by("-price")
    elif sort == "newest":
        products = products.order_by("-created_at")
    elif sort == "popular":
        products = products.order_by("-id")

    return render(request, "search_results.html", {
        "products": products,
        "query": query,
        "selected_category": category,
        "selected_sort": sort,
        "min_price": min_price,
        "max_price": max_price,
        "total_count": products.count(),
    })


# -------------------------
# SEARCH AUTO-SUGGEST API
# -------------------------

def search_suggest(request):
    query = request.GET.get("q", "").strip()
    if not query or len(query) < 2:
        return JsonResponse({"results": []})

    products = Product.objects.filter(
        Q(name__icontains=query) |
        Q(description__icontains=query) |
        Q(category__icontains=query)
    )[:6]

    results = []
    for p in products:
        results.append({
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "price": float(p.price),
            "original_price": float(p.original_price),
            "discount_percent": p.discount_percent,
            "image": p.image.url if p.image else "",
            "url": f"/product/{p.id}/"
        })

    return JsonResponse({"results": results})


# -------------------------
# CATEGORY PAGE
# -------------------------

def category_page(request, category_name):
    products = Product.objects.filter(category=category_name)
    sort = request.GET.get("sort", "").strip()
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()

    if min_price:
        try:
            products = products.filter(price__gte=float(min_price))
        except ValueError:
            pass

    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
        except ValueError:
            pass

    if sort == "price_asc":
        products = products.order_by("price")
    elif sort == "price_desc":
        products = products.order_by("-price")
    elif sort == "newest":
        products = products.order_by("-created_at")
    elif sort == "popular":
        products = products.order_by("-id")

    return render(request, "category.html", {
        "products": products,
        "category_name": category_name,
        "selected_sort": sort,
        "min_price": min_price,
        "max_price": max_price,
        "total_count": products.count(),
    })


# -------------------------
# MY PROFILE
# -------------------------

@login_required(login_url="/login/")
def my_profile(request):
    profile, created = Profile.objects.get_or_create(
        user=request.user,
        defaults={"full_name": request.user.username}
    )

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip()
        mobile = request.POST.get("mobile", "").strip()
        address = request.POST.get("address", "").strip()
        city = request.POST.get("city", "").strip()
        pincode = request.POST.get("pincode", "").strip()

        if full_name:
            profile.full_name = full_name
        profile.mobile = mobile
        profile.address = address
        profile.city = city
        profile.pincode = pincode
        profile.save()

        if email:
            request.user.email = email
            request.user.save()

        messages.success(request, "Your profile and delivery address have been updated successfully!")
        return redirect("my_profile")

    recent_orders = Order.objects.filter(user=request.user)[:5]

    return render(request, "my_profile.html", {
        "profile": profile,
        "recent_orders": recent_orders
    })


# -------------------------
# SIGNUP
# -------------------------

def register_page(request):

    if request.method == "POST":

        full_name = request.POST.get("full_name")
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        # Password check
        if password != confirm_password:
            return render(request, "register.html", {
                "error": "Passwords do not match."
            })

        # Username check
        if User.objects.filter(username=username).exists():
            return render(request, "register.html", {
                "error": "Username already exists."
            })

        # Email check
        if User.objects.filter(email=email).exists():
            return render(request, "register.html", {
                "error": "Email already registered."
            })

        # Generate 6 digit OTP
        otp = str(random.randint(100000, 999999))

        request.session["signup_otp"] = otp

        # Store signup data in session
        mobile = request.POST.get("mobile", "").strip()
        request.session["signup_full_name"] = full_name
        request.session["signup_username"] = username
        request.session["signup_email"] = email
        request.session["signup_mobile"] = mobile
        request.session["signup_password"] = password
        request.session["signup_otp"] = otp

        # Send OTP to email
        send_mail(
        "FashionHub - Email Verification OTP",
        f"Your FashionHub OTP is: {otp}",
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
        )

        return redirect("verify_otp")

    return render(request, "register.html")


# -------------------------
# OTP VERIFICATION
# -------------------------

def verify_otp(request):

    if request.method == "POST":

        entered_otp = request.POST.get("otp")
        saved_otp = request.session.get("signup_otp")

        if entered_otp == saved_otp:

            full_name = request.session.get("signup_full_name")
            username = request.session.get("signup_username")
            email = request.session.get("signup_email")
            mobile = request.session.get("signup_mobile", "")
            password = request.session.get("signup_password")

            # Create User
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )

            # Create Profile
            Profile.objects.create(
                user=user,
                full_name=full_name,
                mobile=mobile
            )

            # Remove signup data from session
            request.session.pop("signup_full_name", None)
            request.session.pop("signup_username", None)
            request.session.pop("signup_email", None)
            request.session.pop("signup_mobile", None)
            request.session.pop("signup_password", None)
            request.session.pop("signup_otp", None)

            return redirect("login")

        else:

            return render(request, "otp.html", {
                "error": "Invalid OTP. Please try again."
            })

    return render(request, "otp.html")


# -------------------------
# LOGIN
# -------------------------

def login_page(request):

    next_url = request.GET.get("next")

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

            if next_url:
                return redirect(next_url)

            return redirect("home")

        else:

            return render(request, "login.html", {
                "error": "Invalid username or password."
            })

    return render(request, "login.html")


# -------------------------
# LOGOUT
# -------------------------

def logout_page(request):

    logout(request)

    return redirect("home")


# -------------------------
# FORGOT PASSWORD & RESET (EMAIL OTP)
# -------------------------

def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        user = User.objects.filter(email=email).first()

        if not user:
            return render(request, "forgot_password.html", {
                "error": "No registered account found with this email address."
            })

        otp = str(random.randint(100000, 999999))
        request.session["reset_email"] = email
        request.session["reset_otp"] = otp

        try:
            send_mail(
                "FashionHub - Password Reset OTP",
                f"Hello {user.username},\n\nYour OTP to reset your FashionHub password is: {otp}\n\nDo not share this OTP with anyone.",
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
        except Exception:
            pass

        return redirect("reset_password")

    return render(request, "forgot_password.html")


def reset_password(request):
    email = request.session.get("reset_email")
    saved_otp = request.session.get("reset_otp")

    if not email or not saved_otp:
        return redirect("forgot_password")

    if request.method == "POST":
        entered_otp = request.POST.get("otp", "").strip()
        new_password = request.POST.get("new_password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()

        if entered_otp != saved_otp:
            return render(request, "reset_password.html", {
                "error": "Invalid OTP code. Please check your email and try again."
            })

        if len(new_password) < 6:
            return render(request, "reset_password.html", {
                "error": "Password must be at least 6 characters long."
            })

        if new_password != confirm_password:
            return render(request, "reset_password.html", {
                "error": "Passwords do not match."
            })

        user = User.objects.filter(email=email).first()
        if user:
            user.set_password(new_password)
            user.save()
            request.session.pop("reset_email", None)
            request.session.pop("reset_otp", None)
            messages.success(request, "Password reset successfully! Please log in with your new password.")
            return redirect("login")

    return render(request, "reset_password.html")


# -------------------------
# PRODUCT DETAIL & REVIEWS
# -------------------------

def product_detail(request, id):
    product = get_object_or_404(Product, id=id)
    reviews = product.reviews.all()
    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = list(Wishlist.objects.filter(user=request.user).values_list("product_id", flat=True))

    return render(request, "product_detail.html", {
        "product": product,
        "reviews": reviews,
        "wishlist_ids": wishlist_ids,
    })


@login_required(login_url="/login/")
def add_review(request, id):
    product = get_object_or_404(Product, id=id)
    if request.method == "POST":
        rating = int(request.POST.get("rating", 5))
        comment = request.POST.get("comment", "").strip()
        if comment:
            Review.objects.create(
                product=product,
                user=request.user,
                rating=max(1, min(5, rating)),
                comment=comment,
            )
            messages.success(request, "Thank you! Your rating & review has been published.")
    return redirect("product_detail", id=product.id)


# -------------------------
# ADD TO CART
# -------------------------

@login_required(login_url="/login/")
def add_to_cart(request, id):
    product = get_object_or_404(Product, id=id)

    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        product=product
    )

    if not created:
        cart_item.quantity += 1
        cart_item.save()

    total_qty = sum(Cart.objects.filter(user=request.user).values_list("quantity", flat=True))

    is_ajax = (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or request.GET.get("ajax") == "1"
        or request.POST.get("ajax") == "1"
    )

    if is_ajax:
        return JsonResponse({
            "status": "success",
            "message": f"{product.name} added to cart!",
            "cart_count": total_qty,
            "product_id": product.id,
            "product_name": product.name,
            "product_price": float(product.price),
            "product_image": product.image.url if product.image else "",
        })

    return redirect(request.META.get("HTTP_REFERER", "cart"))


# -------------------------
# CART
# -------------------------

@login_required(login_url="/login/")
def cart(request):
    cart_items = Cart.objects.filter(user=request.user)
    total = sum(item.subtotal for item in cart_items)
    total_mrp = sum(float(item.product.original_price) * item.quantity for item in cart_items)
    savings = total_mrp - float(total)

    return render(request, "cart.html", {
        "cart_items": cart_items,
        "total": total,
        "total_mrp": total_mrp,
        "savings": max(0, savings),
    })


# -------------------------
# EMAIL HELPER
# -------------------------

def send_order_confirmation_email(order, recipient_email):
    """Sends a professional order confirmation email with plain text + HTML."""
    if not recipient_email:
        return False
    try:
        items = list(order.items.all())
        items_summary = "\n".join([f"- {it.name} (Qty: {it.quantity}) : ₹{it.subtotal}" for it in items])
        subject = f"FashionHub - Order Confirmed! (#{order.order_number})"

        plain_message = (
            f"Hello {order.shipping_name or order.user.username},\n\n"
            f"Thank you for shopping at FashionHub! Your order #{order.order_number} has been placed successfully.\n\n"
            f"ORDER SUMMARY:\n"
            f"Order ID: {order.order_number}\n"
            f"Payment Method: {order.payment_label}\n"
            f"Total Amount: ₹{order.total}\n\n"
            f"ITEMS ORDERED:\n"
            f"{items_summary}\n\n"
            f"DELIVERY ADDRESS:\n"
            f"{order.shipping_name}\n"
            f"{order.shipping_address}, {order.shipping_city} - {order.shipping_pincode}\n"
            f"Phone: +91 {order.shipping_phone}\n\n"
            f"TRACK SHIPMENT:\n"
            f"http://127.0.0.1:8000/my-orders/{order.id}/\n\n"
            f"Courier Partner: BlueDart Express (Estimated Delivery: in 2-3 Days)\n\n"
            f"Thank you for choosing FashionHub!\n"
            f"Warm regards,\n"
            f"FashionHub Customer Support Team"
        )

        item_rows = "".join([
            f"""<tr>
                <td style="padding:10px 12px; border-bottom:1px solid #eee; font-size:14px; color:#333;"><strong>{it.name}</strong></td>
                <td style="padding:10px 12px; border-bottom:1px solid #eee; font-size:14px; color:#666; text-align:center;">{it.quantity}</td>
                <td style="padding:10px 12px; border-bottom:1px solid #eee; font-size:14px; color:#111; text-align:right; font-weight:bold;">&#8377;{it.subtotal}</td>
            </tr>""" for it in items
        ])

        html_message = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family:'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color:#f8f9fa; margin:0; padding:20px;">
          <div style="max-width:600px; margin:0 auto; background:#ffffff; border-radius:12px; overflow:hidden; box-shadow:0 4px 12px rgba(0,0,0,0.06); border:1px solid #e9ecef;">
            <div style="background:linear-gradient(135deg, #ff3f6c, #e02f5a); padding:24px; text-align:center; color:#fff;">
              <h1 style="margin:0; font-size:24px; font-weight:800; letter-spacing:1px;">&#10084; FashionHub</h1>
              <p style="margin:6px 0 0 0; font-size:14px; opacity:0.9;">Order Confirmation Receipt</p>
            </div>
            <div style="padding:28px 24px;">
              <h2 style="margin-top:0; color:#1f2937; font-size:18px;">Thank You, {order.shipping_name or order.user.username}!</h2>
              <p style="color:#4b5563; font-size:14px; line-height:1.5;">Your order <strong>#{order.order_number}</strong> has been received and is being processed by our warehouse.</p>
              
              <div style="background:#f9fafb; border-radius:8px; padding:16px; margin:20px 0; border:1px solid #e5e7eb;">
                <table style="width:100%; font-size:13px; color:#4b5563;">
                  <tr><td><strong>Order ID:</strong></td><td style="text-align:right; font-weight:bold; color:#ff3f6c;">{order.order_number}</td></tr>
                  <tr><td><strong>Payment Method:</strong></td><td style="text-align:right;">{order.payment_label}</td></tr>
                  <tr><td><strong>Estimated Delivery:</strong></td><td style="text-align:right; color:#16a34a; font-weight:bold;">In 2 - 3 Days (BlueDart)</td></tr>
                </table>
              </div>
              
              <h3 style="font-size:15px; color:#1f2937; margin-bottom:10px;">Items Ordered</h3>
              <table style="width:100%; border-collapse:collapse; margin-bottom:20px;">
                <thead>
                  <tr style="background:#f3f4f6;">
                    <th style="padding:8px 12px; text-align:left; font-size:12px; color:#4b5563; text-transform:uppercase;">Product</th>
                    <th style="padding:8px 12px; text-align:center; font-size:12px; color:#4b5563; text-transform:uppercase;">Qty</th>
                    <th style="padding:8px 12px; text-align:right; font-size:12px; color:#4b5563; text-transform:uppercase;">Price</th>
                  </tr>
                </thead>
                <tbody>
                  {item_rows}
                </tbody>
                <tfoot>
                  <tr>
                    <td colspan="2" style="padding:12px; text-align:right; font-size:15px; font-weight:bold; color:#1f2937;">Total Paid:</td>
                    <td style="padding:12px; text-align:right; font-size:16px; font-weight:bold; color:#ff3f6c;">&#8377;{order.total}</td>
                  </tr>
                </tfoot>
              </table>
              
              <div style="background:#fdf2f8; border-left:4px solid #ff3f6c; padding:12px 16px; margin-bottom:24px; border-radius:4px;">
                <strong style="color:#831843; font-size:13px;">Delivery Address:</strong>
                <p style="margin:4px 0 0 0; color:#4b5563; font-size:13px; line-height:1.4;">
                  {order.shipping_name}<br>
                  {order.shipping_address}, {order.shipping_city} - {order.shipping_pincode}<br>
                  Phone: +91 {order.shipping_phone}
                </p>
              </div>
              
              <div style="text-align:center; margin-top:28px;">
                <a href="http://127.0.0.1:8000/my-orders/{order.id}/" style="display:inline-block; background:#ff3f6c; color:#fff; text-decoration:none; padding:12px 28px; border-radius:30px; font-weight:bold; font-size:14px; box-shadow:0 3px 6px rgba(255,63,108,0.3);">
                  Track Shipment Live &rarr;
                </a>
              </div>
            </div>
            <div style="background:#f9fafb; padding:16px; text-align:center; color:#9ca3af; font-size:12px; border-top:1px solid #e5e7eb;">
              &copy; 2026 FashionHub. All rights reserved. &bull; Questions? Reply to this email.
            </div>
          </div>
        </body>
        </html>
        """

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
            html_message=html_message
        )
        print(f"[FashionHub] Email sent successfully to {recipient_email}")
        return True
    except Exception as e:
        print(f"[FashionHub] Error sending email to {recipient_email}: {e}")
        return False


# -------------------------
# CHECKOUT
# -------------------------

@login_required(login_url="/login/")
def checkout_page(request):
    cart_items = Cart.objects.filter(user=request.user)

    if not cart_items.exists():
        return redirect("cart")

    total = sum(item.subtotal for item in cart_items)
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={"full_name": request.user.username}
    )

    total_mrp = sum(float(item.product.original_price) * item.quantity for item in cart_items)
    savings = total_mrp - float(total)

    if request.method == "POST":
        payment_method = request.POST.get("payment_method", "COD")
        shipping_name = request.POST.get("shipping_name", profile.full_name or request.user.username).strip()
        shipping_email = request.POST.get("shipping_email", request.user.email or "arunachalama817@gmail.com").strip()
        shipping_phone = request.POST.get("shipping_phone", profile.mobile).strip()
        shipping_address = request.POST.get("shipping_address", profile.address).strip()
        shipping_city = request.POST.get("shipping_city", profile.city).strip()
        shipping_pincode = request.POST.get("shipping_pincode", profile.pincode).strip()
        save_address = request.POST.get("save_address")

        if shipping_email:
            request.user.email = shipping_email
            request.user.save()

        if save_address:
            profile.full_name = shipping_name
            profile.mobile = shipping_phone
            profile.address = shipping_address
            profile.city = shipping_city
            profile.pincode = shipping_pincode
            profile.save()

        import uuid
        txn_ref = f"PAY-{payment_method.upper()}-{uuid.uuid4().hex[:8].upper()}"


        # Coupon Discount calculation (e.g. FIRST200, FASHION50)
        coupon_code = request.POST.get("coupon_code", "").strip().upper()
        discount = 0.0
        if coupon_code == "FIRST200":
            discount = min(200.0, float(total))
        elif coupon_code == "FASHION50":
            discount = round(float(total) * 0.5, 2)

        order_total = max(0.0, float(total) - discount)

        order = Order.objects.create(
            user=request.user,
            total=order_total,
            payment_method=payment_method,
            shipping_name=shipping_name,
            shipping_email=shipping_email,
            shipping_phone=shipping_phone,
            shipping_address=shipping_address,
            shipping_city=shipping_city,
            shipping_pincode=shipping_pincode,
            transaction_id=txn_ref,
        )

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                name=item.product.name,
                price=item.product.price,
                quantity=item.quantity,
                image=item.product.image.url if item.product.image else "",
            )

        cart_items.delete()
        request.session["last_order_id"] = order.id

        # Send Order Confirmation Email
        recipient_email = shipping_email or request.user.email
        email_sent = False
        if recipient_email:
            print(f"[FashionHub] Triggering confirmation email to {recipient_email} for Order #{order.order_number}...")
            email_sent = send_order_confirmation_email(order, recipient_email)
            request.session["order_email_recipient"] = recipient_email
            request.session["order_email_sent"] = email_sent

        is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
        if is_ajax:
            return JsonResponse({
                "status": "success",
                "order_id": order.id,
                "order_number": order.order_number,
                "redirect_url": "/order-success/"
            })

        return redirect("order_success")

    return render(request, "checkout.html", {
        "cart_items": cart_items,
        "total": total,
        "total_mrp": total_mrp,
        "savings": max(0, savings),
        "profile": profile,
    })


# -------------------------
# ORDER SUCCESS
# -------------------------

@login_required(login_url="/login/")
def order_success(request):
    order_id = request.session.get("last_order_id")
    order = None
    if order_id:
        order = Order.objects.filter(id=order_id, user=request.user).first()
    if not order:
        order = Order.objects.filter(user=request.user).first()

    email_recipient = request.session.get("order_email_recipient", order.shipping_email if order else "")
    email_sent = request.session.get("order_email_sent", True)

    return render(request, "order_success.html", {
        "order": order,
        "email_recipient": email_recipient,
        "email_sent": email_sent,
    })


# -------------------------
# RESEND ORDER CONFIRMATION EMAIL
# -------------------------

@login_required(login_url="/login/")
def resend_order_email(request, id):
    order = get_object_or_404(Order, id=id, user=request.user)
    target_email = request.POST.get("email", order.shipping_email or request.user.email).strip()
    if target_email:
        order.shipping_email = target_email
        order.save()
        ok = send_order_confirmation_email(order, target_email)
        if ok:
            messages.success(request, f"✓ Order confirmation receipt successfully sent to {target_email}! Please check your Inbox / Spam folder.")
        else:
            messages.error(request, f"Unable to deliver email to {target_email}. Please check internet connection or SMTP settings.")
    return redirect("track_order", id=order.id)


# -------------------------
# CART - QUANTITY / REMOVE
# -------------------------

@login_required(login_url="/login/")
def update_cart(request, id, action):
    item = get_object_or_404(Cart, id=id, user=request.user)
    error_msg = None
    item_deleted = False

    if action == "increase":
        if item.quantity < max(item.product.stock, 1):
            item.quantity += 1
            item.save()
        else:
            error_msg = f"Only {item.product.stock} in stock for this item."
            messages.warning(request, error_msg)

    elif action == "decrease":
        if item.quantity > 1:
            item.quantity -= 1
            item.save()
        else:
            item.delete()
            item_deleted = True

    elif action == "remove":
        item.delete()
        item_deleted = True

    is_ajax = (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or request.GET.get("ajax") == "1"
    )

    if is_ajax:
        cart_items = Cart.objects.filter(user=request.user)
        total = sum(i.subtotal for i in cart_items)
        cart_count = sum(cart_items.values_list("quantity", flat=True))
        return JsonResponse({
            "status": "error" if error_msg else "success",
            "error_msg": error_msg,
            "action": action,
            "item_id": id,
            "item_deleted": item_deleted,
            "quantity": 0 if item_deleted else item.quantity,
            "subtotal": 0 if item_deleted else float(item.subtotal),
            "cart_total": float(total),
            "cart_count": cart_count,
            "empty": not cart_items.exists(),
            "message": error_msg or ("Item removed" if item_deleted else "Cart updated")
        })

    return redirect("cart")


# -------------------------
# WISHLIST
# -------------------------

@login_required(login_url="/login/")
def wishlist(request):

    items = Wishlist.objects.filter(user=request.user).select_related("product")

    return render(request, "wishlist.html", {
        "items": items
    })


@login_required(login_url="/login/")
def toggle_wishlist(request, id):

    product = get_object_or_404(Product, id=id)

    obj, created = Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )

    if not created:
        obj.delete()

    # AJAX call (heart icon) -> JSON, normal link -> go back
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "added": created,
            "count": Wishlist.objects.filter(user=request.user).count()
        })

    return redirect(request.META.get("HTTP_REFERER", "wishlist"))


@login_required(login_url="/login/")
def move_to_cart(request, id):

    product = get_object_or_404(Product, id=id)

    cart_item, created = Cart.objects.get_or_create(user=request.user, product=product)
    if not created:
        cart_item.quantity += 1
        cart_item.save()

    Wishlist.objects.filter(user=request.user, product=product).delete()

    return redirect("cart")


# -------------------------
# MY ORDERS + TRACKING
# -------------------------

@login_required(login_url="/login/")
def my_orders(request):
    orders = Order.objects.filter(user=request.user).prefetch_related("items")
    for o in orders:
        o.update_auto_status()

    return render(request, "my_orders.html", {
        "orders": orders
    })


@login_required(login_url="/login/")
def track_order(request, id):
    order = get_object_or_404(Order, id=id, user=request.user)
    order.update_auto_status()

    return render(request, "track_order.html", {
        "order": order
    })


@login_required(login_url="/login/")
def order_status_api(request, id):
    """API for real-time live auto-updating order progress in browser."""
    order = get_object_or_404(Order, id=id, user=request.user)
    order.update_auto_status()
    return JsonResponse({
        "status": order.status,
        "status_display": order.get_status_display(),
        "tracking_steps": order.tracking_steps,
    })


@login_required(login_url="/login/")
def cancel_order(request, id):

    order = get_object_or_404(Order, id=id, user=request.user)

    if request.method == "POST" and order.status in ("Placed", "Confirmed"):
        order.status = "Cancelled"
        order.save()
        messages.success(request, "Order %s cancelled." % order.order_number)

    return redirect("track_order", id=order.id)


@login_required(login_url="/login/")
def advance_order_status(request, id):
    order = get_object_or_404(Order, id=id, user=request.user)
    new_status = request.POST.get("status")

    if new_status and new_status in dict(Order.STATUS_CHOICES):
        order.status = new_status
        order.save()
        messages.success(request, f"Order status updated to '{order.get_status_display()}'!")
    else:
        flow = ['Placed', 'Confirmed', 'Shipped', 'Out for Delivery', 'Delivered']
        if order.status in flow:
            idx = flow.index(order.status)
            next_idx = (idx + 1) % len(flow)
            order.status = flow[next_idx]
            order.save()
            messages.success(request, f"Order progressed to '{order.get_status_display()}'!")

    return redirect("track_order", id=order.id)
