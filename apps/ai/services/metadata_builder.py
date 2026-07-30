"""Metadata Builder — bazadan filtr qiymatlari yig'ish.

Barcha metadata runtime vaqtida bazadan olinadi va LLM ga yuboriladi.
Prompt ichiga hardcode qilinmaydi — shuning uchun:
  - prompt o'zgarmaydi
  - yangi metadata qo'shilganda deploy talab qilinmaydi
  - tokenlar kamayadi
"""

import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

# Cache kaliti va muddati (5 daqiqa)
_CACHE_KEY = "ai_catalog_metadata"
_CACHE_TTL = 300


def build_metadata(use_cache=True):
    """Bazadan barcha filtr qiymatlarini yig'ish.

    Returns:
        dict: {
            "materials": ["Blackout", "Baxmal", ...],
            "colors": ["Oq", "Qora", ...],
            "rooms": ["Yotoqxona", "Oshxona", ...],
            "styles": ["Zamonaviy", "Klassik", ...],
            "categories": ["Shtora", "Tyul", ...],
        }
    """
    if use_cache:
        cached = cache.get(_CACHE_KEY)
        if cached is not None:
            return cached

    from apps.catalog.models import Category, Color, Material, Room, Style

    metadata = {
        "materials": list(
            Material.objects.filter(is_active=True)
            .order_by("sort_order", "name")
            .values_list("name", flat=True)
        ),
        "colors": list(
            Color.objects.all()
            .order_by("name")
            .values_list("name", flat=True)
        ),
        "rooms": list(
            Room.objects.filter(is_active=True)
            .order_by("sort_order", "name")
            .values_list("name", flat=True)
        ),
        "styles": list(
            Style.objects.filter(is_active=True)
            .order_by("sort_order", "name")
            .values_list("name", flat=True)
        ),
        "categories": list(
            Category.objects.filter(is_active=True)
            .order_by("sort_order", "name")
            .values_list("name", flat=True)
        ),
    }

    if use_cache:
        cache.set(_CACHE_KEY, metadata, _CACHE_TTL)

    logger.debug(
        "Metadata built: %d materials, %d colors, %d rooms, %d styles, %d categories",
        len(metadata["materials"]),
        len(metadata["colors"]),
        len(metadata["rooms"]),
        len(metadata["styles"]),
        len(metadata["categories"]),
    )
    return metadata


def invalidate_metadata_cache():
    """Metadata keshini tozalash (admin panel dan ma'lumot o'zgarganda)."""
    cache.delete(_CACHE_KEY)
