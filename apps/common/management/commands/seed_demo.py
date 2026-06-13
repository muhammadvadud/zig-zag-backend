from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import Category, Color, Product, ProductVariant
from apps.services.models import ServiceTariff


class Command(BaseCommand):
    help = "Populate the database with demo catalog and service data."

    @transaction.atomic
    def handle(self, *args, **options):
        self._tariffs()
        colors = self._colors()
        self._catalog(colors)
        self.stdout.write(self.style.SUCCESS("Demo ma'lumotlar yuklandi."))

    def _tariffs(self):
        data = [
            ("smart", "Smart", "Смарт", 0, None, False, ["Bepul maslahat", "Kafolat"], True, False, 20000, 0),
            ("lux", "Lux", "Люкс", 0, 24990, True, ["Bepul maslahat", "Tikish", "Kafolat", "Sun'iy rasm"], True, True, 60000, 10),
            ("premium", "Premium", "Премиум", 0, 39990, False, ["Hammasi", "O'lchov", "O'rnatish", "Maxsus dizayn"], True, True, 150000, 30),
        ]
        for code, nu, nr, price, ppm, pop, feats, chat, img, tok, imgs in data:
            ServiceTariff.objects.update_or_create(
                code=code,
                defaults={
                    "name_uz": nu,
                    "name_ru": nr,
                    "price": price,
                    "price_per_m2": ppm,
                    "is_popular": pop,
                    "features": {"uz": feats, "ru": feats},
                    "ai_chat_enabled": chat,
                    "ai_image_enabled": img,
                    "ai_monthly_token_limit": tok,
                    "ai_image_monthly_limit": imgs,
                },
            )

    def _colors(self):
        palette = [
            ("Krem", "Крем", "#EBE3D5"),
            ("Charcoal", "Графит", "#36454F"),
            ("Oat", "Овсяный", "#D9C9A3"),
            ("Noir", "Чёрный", "#1A1A1A"),
        ]
        colors = {}
        for nu, nr, hex_ in palette:
            color, _ = Color.objects.get_or_create(name_uz=nu, defaults={"name_ru": nr, "hex": hex_})
            colors[nu] = color
        return colors

    def _catalog(self, colors):
        categories = [
            ("linen", "Linen", "Лён"),
            ("velvet", "Velvet", "Бархат"),
            ("sheer", "Sheer", "Тюль"),
            ("blackout", "Blackout", "Блэкаут"),
            ("silk", "Silk", "Шёлк"),
        ]
        cat_objs = {}
        for i, (slug, nu, nr) in enumerate(categories):
            cat, _ = Category.objects.update_or_create(
                slug=slug, defaults={"name_uz": nu, "name_ru": nr, "sort_order": i}
            )
            cat_objs[slug] = cat

        products = [
            ("linen-sahar", "linen", "Linen Sahar", "Лён Сахар", "linen", 1250000, True),
            ("velvet-shoh", "velvet", "Velvet Shoh", "Бархат Шох", "velvet", 1890000, False),
            ("blackout-noir", "blackout", "Blackout Noir", "Блэкаут Нуар", "blackout", 1650000, True),
            ("sheer-nur", "sheer", "Sheer Nur", "Тюль Нур", "sheer", 890000, False),
        ]
        sku = 1000
        for slug, cat_slug, nu, nr, mat, price, is_new in products:
            product, _ = Product.objects.update_or_create(
                slug=slug,
                defaults={
                    "category": cat_objs[cat_slug],
                    "name_uz": nu,
                    "name_ru": nr,
                    "material": mat,
                    "base_price": Decimal(price),
                    "is_new": is_new,
                    "stock": 50,
                },
            )
            for color in list(colors.values())[:3]:
                sku += 1
                ProductVariant.objects.get_or_create(
                    product=product,
                    color=color,
                    defaults={"sku": f"ZZ-{sku}", "stock": 20},
                )
