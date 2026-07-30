"""Product Search — filtrlar asosida mahsulot qidirish.

Barcha filtr turlari (material, rang, xona, uslub, kategoriya, o'lcham)
bo'yicha bazadan mahsulotlarni qidiradi.

Filter qiymatlari foydalanuvchi tilida keladi (AI dan),
shuning uchun name_uz va name_ru bo'yicha iexact qidiriladi.
"""

import logging

from django.db.models import Q

from apps.catalog.models import Product

logger = logging.getLogger(__name__)


def search_products(filters, limit=6):
    """Filtrlar asosida mahsulotlarni qidirish.

    Args:
        filters: dict — filter_extractor dan kelgan filtrlar.
            {
                "materials": [...],
                "colors": [...],
                "room": "..." | None,
                "style": "..." | None,
                "category": "..." | None,
                "width": float | None,
                "height": float | None,
            }
        limit: int — qaytariladigan maksimal mahsulotlar soni.

    Returns:
        list of dict: [{id, title, slug, image}, ...]
    """
    if not filters or not isinstance(filters, dict):
        return []

    # "filters" kaliti ichida bo'lishi mumkin
    f = filters.get("filters", filters)

    qs = Product.objects.filter(is_active=True, is_deleted=False)

    has_filter = False

    # Material filtri
    materials = f.get("materials", [])
    if materials:
        material_q = Q()
        for mat in materials:
            material_q |= Q(materials__name__iexact=mat)
            material_q |= Q(materials__name_uz__iexact=mat)
            material_q |= Q(materials__name_ru__iexact=mat)
        qs = qs.filter(material_q)
        has_filter = True

    # Rang filtri
    colors = f.get("colors", [])
    if colors:
        color_q = Q()
        for clr in colors:
            color_q |= Q(colors__name__iexact=clr)
            color_q |= Q(colors__name_uz__iexact=clr)
            color_q |= Q(colors__name_ru__iexact=clr)
        qs = qs.filter(color_q)
        has_filter = True

    # Xona filtri
    room = f.get("room")
    if room:
        qs = qs.filter(
            Q(rooms__name__iexact=room)
            | Q(rooms__name_uz__iexact=room)
            | Q(rooms__name_ru__iexact=room)
        )
        has_filter = True

    # Uslub filtri
    style = f.get("style")
    if style:
        qs = qs.filter(
            Q(styles__name__iexact=style)
            | Q(styles__name_uz__iexact=style)
            | Q(styles__name_ru__iexact=style)
        )
        has_filter = True

    # Kategoriya filtri
    category = f.get("category")
    if category:
        qs = qs.filter(
            Q(category__name__iexact=category)
            | Q(category__name_uz__iexact=category)
            | Q(category__name_ru__iexact=category)
        )
        has_filter = True

    if not has_filter:
        return []

    qs = qs.prefetch_related("images").distinct()[:limit]

    results = []
    for p in qs:
        main_img = p.images.filter(is_main=True).first()
        if not main_img:
            main_img = p.images.first()
        image_url = main_img.image.url if main_img and main_img.image else None

        results.append({
            "id": p.id,
            "title": p.name,
            "slug": p.slug,
            "image": image_url,
        })

    logger.debug("Product search: %d results for filters %s", len(results), f)
    return results
