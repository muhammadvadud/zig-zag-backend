"""Download curtain photos and attach them to demo products as ProductImage.

Run after `seed_demo`. Idempotent: clears a product's existing images before
re-adding. Images are downloaded from the web and stored in MEDIA_ROOT, so the
API serves real `main_image`/`images` instead of the frontend faking them.
"""

import urllib.request

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import Product, ProductImage

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"


def _unsplash(photo_id, w=1000):
    return f"https://images.unsplash.com/photo-{photo_id}?w={w}&q=80"


# Per product: a main hero shot + one photo per variant (in variant order).
# Variants are seeded as Krem / Charcoal / Oat for every product, so we pick
# category-appropriate curtain photos by position rather than by colour name.
PRODUCT_IMAGES = {
    "linen-sahar": {
        "main": _unsplash("1540518614846-7eded433c457"),
        "variants": [
            _unsplash("1540518614846-7eded433c457"),
            _unsplash("1567538096630-e0c55bd6374c"),
            _unsplash("1493663284031-b7e3aefcae8e"),
        ],
    },
    "velvet-shoh": {
        "main": _unsplash("1556228578-8c89e6adf883"),
        "variants": [
            _unsplash("1556228578-8c89e6adf883"),
            _unsplash("1631679706909-1844bbd07221"),
            _unsplash("1556228453-efd6c1ff04f6"),
        ],
    },
    "blackout-noir": {
        "main": _unsplash("1513161455079-7dc1de15ef3e"),
        "variants": [
            _unsplash("1513161455079-7dc1de15ef3e"),
            _unsplash("1631679706909-1844bbd07221"),
            _unsplash("1493663284031-b7e3aefcae8e"),
        ],
    },
    "sheer-nur": {
        "main": _unsplash("1494438639946-1ebd1d20bf85"),
        "variants": [
            _unsplash("1494438639946-1ebd1d20bf85"),
            _unsplash("1505693416388-ac5ce068fe85"),
            _unsplash("1567538096630-e0c55bd6374c"),
        ],
    },
}


class Command(BaseCommand):
    help = "Download curtain photos and attach them to demo products."

    def _download(self, url):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()

    @transaction.atomic
    def handle(self, *args, **options):
        for slug, spec in PRODUCT_IMAGES.items():
            try:
                product = Product.objects.prefetch_related("variants").get(slug=slug)
            except Product.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"skip {slug}: product yo'q"))
                continue

            product.images.all().delete()

            # Main product-level hero image (shown for every variant).
            data = self._download(spec["main"])
            main = ProductImage(product=product, is_main=True, sort_order=0)
            main.image.save(f"{slug}-main.jpg", ContentFile(data), save=True)

            # One photo per variant.
            for i, (variant, url) in enumerate(zip(product.variants.all(), spec["variants"])):
                data = self._download(url)
                img = ProductImage(product=product, variant=variant, sort_order=i + 1)
                img.image.save(f"{slug}-{variant.id}.jpg", ContentFile(data), save=True)

            self.stdout.write(self.style.SUCCESS(f"{slug}: {product.images.count()} rasm"))

        self.stdout.write(self.style.SUCCESS("Mahsulot rasmlari yuklandi."))
