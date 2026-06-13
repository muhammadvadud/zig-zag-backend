from .models import Cart


def get_or_create_cart(request):
    """Resolve the active cart: by user when logged in, else by session key."""

    user = request.user if request.user.is_authenticated else None
    if user:
        cart, _ = Cart.objects.get_or_create(user=user)
        return cart

    if not request.session.session_key:
        request.session.save()
    session_key = request.session.session_key
    cart, _ = Cart.objects.get_or_create(session_key=session_key, user__isnull=True)
    return cart


def merge_session_cart(session_key, user):
    """Move items from an anonymous session cart into the user's cart."""

    if not session_key:
        return
    session_cart = Cart.objects.filter(session_key=session_key, user__isnull=True).first()
    if not session_cart:
        return

    user_cart, _ = Cart.objects.get_or_create(user=user)
    for item in session_cart.items.all():
        existing = user_cart.items.filter(
            variant=item.variant,
            width_cm=item.width_cm,
            height_cm=item.height_cm,
            service_tariff=item.service_tariff,
        ).first()
        if existing:
            existing.quantity += item.quantity
            existing.save(update_fields=["quantity", "updated_at"])
            item.delete()
        else:
            item.cart = user_cart
            item.save(update_fields=["cart", "updated_at"])
    session_cart.delete()
