from datetime import datetime

from django.db import transaction

from apps.catalog.models import ProductVariant
from apps.common.exceptions import BusinessError

from .models import Order, OrderItem

# Allowed forward status transitions (the order lifecycle is one-directional).
# "pending" -> "paid" bu yerda YO'Q ataylab: to'lov holatini faqat haqiqiy
# to'lov webhook'lari (apps/payments/click.py, payme.py) o'zgartiradi, xodim/
# manager qo'lda "to'landi" deb belgilay olmaydi. Shu sabab "processing" ham
# yo'q — to'lovsiz buyurtmani ishga tushirib bo'lmaydi.
STATUS_FLOW = {
    "pending": {"cancelled"},
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
    # select_for_update: without a row lock two concurrent checkouts can both
    # read the same "last" order and compute the same seq, then collide on the
    # order_number unique constraint (IntegrityError -> 500). The caller always
    # wraps this in @transaction.atomic, so the lock is held only for the
    # duration of create_order_from_cart and is released at commit.
    last = (
        Order.objects.select_for_update()
        .filter(order_number__startswith=f"ZZ-{year}-")
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
def create_order_from_cart(user, cart, address=None, comment="", payment_provider=""):
    """Build an order from the cart, recomputing every price server-side.

    Mahsulotlar buyurtmaga qarab tikiladi — ombor (stok) tekshiruvi yo'q.
    """

    items = list(cart.items.select_related("variant__product", "color", "service_tariff").all())
    if not items:
        raise BusinessError("Savat bo'sh.")

    order = Order.objects.create(
        order_number=generate_order_number(),
        user=user,
        address=address,
        comment=comment,
        payment_provider=payment_provider or "",
    )

    subtotal = 0
    for item in items:
        variant = ProductVariant.objects.select_related("product").get(pk=item.variant_id)
        product = variant.product
        # Savatga qo'shilgandan keyin mahsulot/variant sotuvdan olib tashlangan
        # yoki soft-delete qilingan bo'lishi mumkin — checkout paytida qayta
        # tekshiramiz, aks holda mijoz endi mavjud bo'lmagan mahsulotni sotib
        # olib qo'yishi mumkin edi.
        if variant.is_deleted or not variant.is_active or product.is_deleted or not product.is_active:
            raise BusinessError(
                f"“{product.name_uz}” endi mavjud emas — savatdan olib tashlang va qayta urinib ko'ring."
            )

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
            service_tariff=item.service_tariff,
            line_total=line_total,
        )
        subtotal += line_total

    order.subtotal = subtotal
    order.total = subtotal + order.delivery_fee - order.discount
    order.save(update_fields=["subtotal", "total", "updated_at"])

    cart.items.all().delete()
    return order
