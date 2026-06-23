import urllib.request
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Avg

from apps.catalog.models import (
    Banner,
    Category,
    Collection,
    Color,
    HeroContent,
    Product,
    ProductVariant,
    Review,
    Room,
    Style,
    Tailor,
)
from apps.services.models import ServiceTariff

_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"


def _download(url):
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


class Command(BaseCommand):
    help = "Populate the database with demo catalog and service data."

    @transaction.atomic
    def handle(self, *args, **options):
        self._tariffs()
        colors = self._colors()
        styles = self._styles()
        rooms = self._rooms()
        tailors = self._tailors()
        self._catalog(colors, styles, rooms, tailors)
        self._hero()
        self._banners()
        self._collections()
        self._reviews()
        self.stdout.write(self.style.SUCCESS("Demo ma'lumotlar yuklandi."))

    def _tariffs(self):
        # code, name_uz, name_ru, price, price_per_m2, is_popular, feats_uz, feats_ru
        data = [
            ("smart", "Smart", "Смарт", 0, None, False,
             ["Bepul maslahat", "Tikish", "Kafolat"],
             ["Бесплатная консультация", "Пошив", "Гарантия"]),
            ("lux", "Lux", "Люкс", 0, 24990, True,
             ["Bepul maslahat", "Tikish", "Kafolat", "Sun'iy rasm", "Maxsus dizayn"],
             ["Бесплатная консультация", "Пошив", "Гарантия", "AI-визуализация", "Дизайн под интерьер"]),
            ("premium", "Premium", "Премиум", 0, 59990, False,
             ["Bepul maslahat", "Tikish", "Kafolat", "Sun'iy rasm", "Maxsus dizayn", "O'lchov", "O'rnatish"],
             ["Бесплатная консультация", "Пошив", "Гарантия", "AI-визуализация", "Дизайн под интерьер", "Замер", "Монтаж"]),
        ]
        for i, (code, nu, nr, price, ppm, pop, fu, fr) in enumerate(data):
            ServiceTariff.objects.update_or_create(
                code=code,
                defaults={
                    "name_uz": nu,
                    "name_ru": nr,
                    "price": price,
                    "price_per_m2": ppm,
                    "is_popular": pop,
                    "features_uz": fu,
                    "features_ru": fr,
                    "sort_order": i,
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

    def _styles(self):
        # slug, name_uz, name_ru, blurb_uz, blurb_ru, png file (in MEDIA_ROOT/styles/)
        data = [
            ("hitech", "Hi-Tech", "Хай-тек", "Aniq chiziqlar, motorli", "Чёткие линии, моторизация", "hitech.png"),
            ("classic", "Klassik", "Классика", "Lambrekenlar, ipak", "Ламбрекены, шёлк", "classic.png"),
            ("modern", "Zamonaviy", "Модерн", "Sokin, ko'p qatlamli", "Спокойный, многослойный", "fashion.png"),
            ("minimal", "Minimal", "Минимализм", "Kam mato, ko'p yorug'lik", "Меньше ткани, больше света", "minimal.png"),
            ("loft", "Loft", "Лофт", "Metall karniz, qora", "Металл, чёрный", "loft.png"),
            ("provence", "Provans", "Прованс", "Linen, pastel", "Лён, пастель", "provans.png"),
            ("boho", "Boho", "Бохо", "Pop ranglar, naqshlar", "Цвет, узоры", "boho.png"),
            ("artdeco", "Art Deco", "Ар-деко", "Velvet, jihozli", "Велюр, фурнитура", "artdeco.png"),
            ("scandi", "Skandi", "Сканди", "Och ranglar, tabiiy mato", "Светлый, натуральный", "skandi.png"),
        ]
        styles = {}
        for i, (slug, nu, nr, bu, br, png) in enumerate(data):
            style, _ = Style.objects.update_or_create(
                slug=slug,
                defaults={
                    "name_uz": nu, "name_ru": nr,
                    "blurb_uz": bu, "blurb_ru": br,
                    "sort_order": i,
                },
            )
            # Lokal style PNG MEDIA_ROOT/styles/ ga oldindan ko'chiriladi (docker cp).
            src = Path(settings.MEDIA_ROOT) / "styles" / png
            if src.exists() and not style.image:
                style.image.name = f"styles/{png}"
                style.save(update_fields=["image"])
            styles[slug] = style
        return styles

    def _rooms(self):
        data = [
            ("living", "Mehmonxona", "Гостиная"),
            ("bedroom", "Yotoqxona", "Спальня"),
            ("kids", "Bolalar", "Детская"),
            ("office", "Ofis", "Офис"),
        ]
        rooms = {}
        for i, (slug, nu, nr) in enumerate(data):
            room, _ = Room.objects.update_or_create(
                slug=slug, defaults={"name_uz": nu, "name_ru": nr, "sort_order": i}
            )
            rooms[slug] = room
        return rooms

    def _tailors(self):
        data = [
            ("Dilnoza Yusupova", "Дилноза Юсупова", "DY", "Linen · Sheer", "Лён · Тюль", "4.9", 187),
            ("Mohira Karimova", "Мохира Каримова", "MK", "Velvet · Silk", "Бархат · Шёлк", "4.8", 143),
            ("Feruza Xasanova", "Феруза Хасанова", "FX", "Blackout · Velvet", "Блекаут · Бархат", "4.9", 215),
            ("Nodira Toshmatova", "Нодира Тошматова", "NT", "Silk · Sheer", "Шёлк · Тюль", "4.7", 98),
            ("Hulkar Rahimova", "Хулкар Рахимова", "HR", "Linen · Blackout", "Лён · Блекаут", "4.8", 162),
        ]
        tailors = []
        for i, (nu, nr, initials, spu, spr, rating, orders) in enumerate(data):
            tailor, _ = Tailor.objects.update_or_create(
                initials=initials,
                defaults={
                    "name_uz": nu, "name_ru": nr,
                    "specialty_uz": spu, "specialty_ru": spr,
                    "rating": Decimal(rating), "orders_count": orders,
                    "sort_order": i,
                },
            )
            tailors.append(tailor)
        return tailors

    def _catalog(self, colors, styles, rooms, tailors=None):
        tailors = tailors or []
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

        # slug, cat, name_uz, name_ru, material, price, is_new, [style slugs], [room slugs]
        products = [
            ("linen-sahar", "linen", "Linen Sahar", "Лён Сахар", "linen", 1250000, True,
             ["provence", "scandi", "minimal"], ["living", "bedroom"]),
            ("velvet-shoh", "velvet", "Velvet Shoh", "Бархат Шох", "velvet", 1890000, False,
             ["classic", "artdeco"], ["living", "bedroom"]),
            ("blackout-noir", "blackout", "Blackout Noir", "Блэкаут Нуар", "blackout", 1650000, True,
             ["loft", "hitech", "modern"], ["bedroom", "office"]),
            ("sheer-nur", "sheer", "Sheer Nur", "Тюль Нур", "sheer", 890000, False,
             ["minimal", "scandi", "modern"], ["living", "kids"]),
        ]
        sku = 1000
        for pi, (slug, cat_slug, nu, nr, mat, price, is_new, style_slugs, room_slugs) in enumerate(products):
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
                    "tailor": tailors[pi % len(tailors)] if tailors else None,
                },
            )
            product.styles.set([styles[s] for s in style_slugs if s in styles])
            product.rooms.set([rooms[r] for r in room_slugs if r in rooms])
            for color in list(colors.values())[:3]:
                sku += 1
                ProductVariant.objects.get_or_create(
                    product=product,
                    color=color,
                    defaults={"sku": f"ZZ-{sku}", "stock": 20},
                )

    def _hero(self):
        HeroContent.objects.update_or_create(
            sort_order=0,
            defaults={
                "eyebrow_uz": "Zig Zag · Premium pardalar",
                "eyebrow_ru": "Премиум шторы · Узбекистан",
                "title_uz": "Uy — sizniki, Uslub ham",
                "title_ru": "Тихая комната,",
                "title_italic_uz": "shunday bo‘lsin..",
                "title_italic_ru": "тихая жизнь.",
                "description_uz": "Linen, velvet, sheer va ipakdan tikilgan premium pardalar. "
                "Uyingizda tanlash, 24 soat ichida o'lchov.",
                "description_ru": "Премиальные шторы из льна, велюра, тюля и шёлка. "
                "Подбор у себя дома, замер за 24 часа.",
                "stat1_value_uz": "12 yil", "stat1_value_ru": "12 лет",
                "stat1_label_uz": "tajriba", "stat1_label_ru": "на рынке",
                "stat2_value_uz": "2 400+", "stat2_value_ru": "2 400+",
                "stat2_label_uz": "mijozlar", "stat2_label_ru": "клиентов",
                "stat3_value_uz": "24h", "stat3_value_ru": "24h",
                "stat3_label_uz": "o'lchov", "stat3_label_ru": "замер",
                "is_active": True,
            },
        )

    def _banners(self):
        data = [
            ("Bukhara · 2026", "Bukhara · 2026", "Бухара · 2026",
             "Yangi kolleksiya", "Новая коллекция",
             "Qo'l bilan to'qilgan ipak pardalar", "Шёлковые шторы ручной работы",
             "Ko'rish", "Смотреть", "/catalog",
             "https://images.unsplash.com/photo-1567538096630-e0c55bd6374c?w=1400&q=80"),
            ("Sokin uy", "Sokin uy", "Тихий дом",
             "Ofis interyer", "Интерьер офиса",
             "Linen va sheer pardalar", "Льняные и тюлевые шторы",
             "Kashf qilish", "Открыть", "/catalog",
             "https://images.unsplash.com/photo-1540518614846-7eded433c457?w=1400&q=80"),
            ("−25% Velvet", "−25% Velvet", "−25% Велюр",
             "Maxsus taklif", "Спецпредложение",
             "Faqat shu hafta", "Только на этой неделе",
             "Sotib olish", "Купить", "/catalog",
             "https://images.unsplash.com/photo-1556228453-efd6c1ff04f6?w=1400&q=80"),
        ]
        for i, (_t, tu, tr, eu, er, su, sr, cu, cr, link, url) in enumerate(data):
            banner, _ = Banner.objects.update_or_create(
                sort_order=i,
                defaults={
                    "title_uz": tu, "title_ru": tr,
                    "eyebrow_uz": eu, "eyebrow_ru": er,
                    "subtitle_uz": su, "subtitle_ru": sr,
                    "cta_uz": cu, "cta_ru": cr,
                    "link": link,
                },
            )
            if not banner.image:
                banner.image.save(f"banner-{i}.jpg", ContentFile(_download(url)), save=True)

    def _collections(self):
        data = [
            ("bukhara-2026", "Bukhara 2026", "Бухара 2026",
             ["linen-sahar", "sheer-nur"],
             "https://images.unsplash.com/photo-1513161455079-7dc1de15ef3e?w=1400&q=80"),
            ("velvet-lux", "Velvet Lux", "Бархат Люкс",
             ["velvet-shoh", "blackout-noir"],
             "https://images.unsplash.com/photo-1556228453-efd6c1ff04f6?w=1400&q=80"),
        ]
        for i, (slug, tu, tr, prod_slugs, url) in enumerate(data):
            collection, _ = Collection.objects.update_or_create(
                slug=slug,
                defaults={"title_uz": tu, "title_ru": tr, "sort_order": i},
            )
            collection.products.set(Product.objects.filter(slug__in=prod_slugs))
            if not collection.image:
                collection.image.save(f"{slug}.jpg", ContentFile(_download(url)), save=True)

    def _reviews(self):
        User = get_user_model()
        reviewers = [
            ("+998901112233", "Dilnoza Karimova"),
            ("+998901112244", "Sardor Aliyev"),
            ("+998901112255", "Malika Rashidova"),
            ("+998901112266", "Jasur To'rayev"),
        ]
        users = []
        for phone, name in reviewers:
            user, _ = User.objects.get_or_create(
                phone=phone, defaults={"full_name": name, "is_phone_verified": True}
            )
            users.append(user)
        comments = [
            (5, "Sifati zo'r, rangi rasmga to'liq mos keldi. Tavsiya qilaman."),
            (4, "Yaxshi parda, yetkazib berish tez bo'ldi."),
            (5, "Uy interyeriga juda yarashdi, rahmat!"),
            (4, "Mato zich, yorug'likni yaxshi to'sadi."),
        ]
        for product in Product.objects.all():
            for user, (rating, text) in zip(users, comments):
                Review.objects.update_or_create(
                    product=product,
                    user=user,
                    defaults={"rating": rating, "comment": text, "is_published": True},
                )
            agg = product.reviews.filter(is_published=True).aggregate(a=Avg("rating"))["a"] or 0
            product.rating_avg = round(Decimal(agg), 2)
            product.save(update_fields=["rating_avg"])
