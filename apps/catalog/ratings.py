"""Sharhlar asosida mahsulot va chevar (usta) baholarini qayta hisoblash.

Mahsulot `rating_avg` — o'sha mahsulotning e'lon qilingan sharhlaridagi mahsulot
bahosining (rating) o'rtachasi. Chevar `rating` — o'sha chevarga biriktirilgan
mahsulotlarning e'lon qilingan sharhlaridagi chevar bahosining (rating_tailor,
faqat berilganlari) o'rtachasi.
"""

from decimal import Decimal

from django.db.models import Avg


def recompute_tailor_rating(tailor):
    if tailor is None:
        return
    from .models import Review

    agg = (
        Review.objects.filter(
            product__tailor=tailor, is_published=True, rating_tailor__gt=0
        ).aggregate(a=Avg("rating_tailor"))["a"]
    )
    tailor.rating = round(Decimal(agg), 2) if agg else Decimal("0")
    tailor.save(update_fields=["rating"])


def recompute_product_rating(product):
    if product is None:
        return
    agg = product.reviews.filter(is_published=True).aggregate(a=Avg("rating"))["a"]
    product.rating_avg = round(Decimal(agg), 2) if agg else Decimal("0")
    product.save(update_fields=["rating_avg"])
    if product.tailor_id:
        recompute_tailor_rating(product.tailor)
