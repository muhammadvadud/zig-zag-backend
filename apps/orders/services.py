from datetime import datetime

from django.db import transaction

from apps.catalog.models import ProductVariant
from apps.common.exceptions import BusinessError

from .models import Order, OrderItem

# Allowed forward status transitions (the order lifecycle is one-directional).
STATUS_FLOW = {
    "pending": {"paid", "processing", "cancelled"},
    "paid": {"processing", "measuring", "cancelled", "refunded"},
    "processing": {"measuring", "sewing", "shipped", "cancelled"},
    "measuring": {"sewing", "cancelled"},
    "sewing": {"shipped", "cancelled"},
    "shipped": {"completed"},
    "completed": set(),
    "cancelled": set(),
    "refunded": set(),
}


def can_transition(current, new):
    return new in STATUS_FLOW.get(current, set())


def generate_order_number():
    year = datetime.now().year
    last = (
        Order.objects.filter(order_number__startswith=f"ZZ-{year}-")
        .order_by("-id")
        .first()
    )
    seq = 1
    if last:
        try:
            seq = int(last.order_number.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = Order.objects.count() + 1
    return f"ZZ-{year}-{seq:06d}"


@transaction.atomic
def create_order_from_cart(
    user,
    cart,
    address=None,
    comment="",
    payment_provider="",
    recipient_full_name="",
    recipient_phone="",
):
    """Build an order from the cart, recomputing every price server-side.

    Mahsulotlar buyurtmaga qarab tikiladi — ombor (stok) tekshiruvi yo'q.
    """

    items = list(cart.items.select_related("variant__product", "color", "service_tariff").all())
    if not items:
        raise BusinessError("Savat bo'sh.")

    service_tariff_ids = {item.service_tariff_id for item in items if item.service_tariff_id}
    if len(service_tariff_ids) > 1:
        raise BusinessError("Bitta buyurtmada faqat bitta xizmat tarifi bo'lishi mumkin.")
    service_tariff_id = next(iter(service_tariff_ids), None)

    order = Order.objects.create(
        order_number=generate_order_number(),
        user=user,
        address=address,
        comment=comment,
        payment_provider=payment_provider or "",
        recipient_full_name=recipient_full_name,
        recipient_phone=recipient_phone,
        service_tariff_id=service_tariff_id,
    )

    subtotal = 0
    for item in items:
        variant = ProductVariant.objects.select_related("product").get(pk=item.variant_id)
        # Buyurtmaga qarab ishlab chiqariladi — ombor (stok) tekshiruvi yo'q.
        product = variant.product

        # Prices are taken from the server-side computation, never the client.
        unit_price = item.unit_price + item.service_cost
        line_total = item.line_total
        OrderItem.objects.create(
            order=order,
            variant=variant,
            color=item.color,
            product_name_snapshot=product.name_uz,
            unit_price=unit_price,
            quantity=item.quantity,
            width_cm=item.width_cm,
            height_cm=item.height_cm,
            line_total=line_total,
        )
        subtotal += line_total

    order.subtotal = subtotal
    order.total = subtotal + order.delivery_fee - order.discount
    order.save(update_fields=["subtotal", "total", "updated_at"])

    cart.items.all().delete()
    return order
