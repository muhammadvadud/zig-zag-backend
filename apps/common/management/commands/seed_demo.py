import random
import urllib.request
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Avg
from django.utils import timezone

from apps.accounts.models import Address
from apps.catalog.models import (
    Banner,
    Category,
    Collection,
    Color,
    HeroContent,
    Product,
    ProductImage,
    ProductVariant,
    Review,
    Room,
    Style,
    Tailor,
    Testimonial,
    Work,
)
from apps.orders.models import MeasurementRequest, Order, OrderItem
from apps.payments.models import Payment
from apps.services.models import ServiceTariff

# Phone prefix that marks a user as demo-seeded (safe to flush).
DEMO_PHONE_PREFIX = "+99893"

_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"


def _download(url):
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


class Command(BaseCommand):
    help = "Populate the database with demo catalog, orders and dashboard data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete prior demo orders/payments/reviews/measurements/tailors/customers first.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options.get("flush"):
            self._flush()

        self._tariffs()
        colors = self._colors()
        styles = self._styles()
        rooms = self._rooms()
        tailors = self._tailors()
        self._catalog(colors, styles, rooms, tailors)
        self._hero()
        self._banners()
        self._collections()
        self._testimonials()
        self._works(rooms)
        self._reviews()

        self._ensure_product_assets(colors)
        customers = self._customers()
        orders = self._orders(customers)
        self._measurements(customers)
        self._extra_reviews(customers)

        self.stdout.write(self.style.SUCCESS("Demo ma'lumotlar yuklandi."))
        self.stdout.write("--- Summary ---")
        self.stdout.write(f"Tailors:      {Tailor.objects.count()}")
        self.stdout.write(f"Products:     {Product.objects.count()}")
        self.stdout.write(f"Variants:     {ProductVariant.objects.count()}")
        self.stdout.write(f"Customers:    {get_user_model().objects.filter(role='customer').count()}")
        self.stdout.write(f"Orders:       {Order.objects.count()}")
        self.stdout.write(f"Order items:  {OrderItem.objects.count()}")
        self.stdout.write(f"Payments:     {Payment.objects.count()}")
        self.stdout.write(f"Reviews:      {Review.objects.count()} (unpublished: {Review.objects.filter(is_published=False).count()})")
        self.stdout.write(f"Measurements: {MeasurementRequest.objects.count()}")

    def _flush(self):
        OrderItem.objects.all().delete()
        Payment.objects.all().delete()
        MeasurementRequest.objects.all().delete()
        Order.objects.all().delete()
        Review.objects.all().delete()
        Tailor.objects.all().delete()
        # Demo customers (seeded with the DEMO_PHONE_PREFIX); keep admin/managers.
        get_user_model().objects.filter(
            role="customer", phone__startswith=DEMO_PHONE_PREFIX
        ).delete()

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
            ("Sabina Azimova", "Сабина Азимова", "SA", "Sheer · Silk", "Тюль · Шёлк", "4.3", 74),
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
        # O'lcham rejimi (size_mode): tayyor o'lcham / faqat mijoz o'lchami / ikkalasi.
        size_modes = {
            "linen-sahar": "both",      # tayyor o'lchamlar + o'z o'lchami
            "velvet-shoh": "variant",   # faqat tayyor o'lchamlar
            "blackout-noir": "variant",
            "sheer-nur": "custom",      # faqat o'lchov bo'yicha (custom_only avtomatik)
        }
        # Custom/both mahsulotlar uchun 1 m² narxi (per-m²) — mijoz o'z o'lchamini kiritganda.
        per_m2 = {"linen-sahar": Decimal("350000"), "sheer-nur": Decimal("250000")}
        for pi, (slug, cat_slug, nu, nr, mat, price, is_new, style_slugs, room_slugs) in enumerate(products):
            product, _ = Product.objects.update_or_create(
                slug=slug,
                defaults={
                    "category": cat_objs[cat_slug],
                    "name_uz": nu,
                    "name_ru": nr,
                    "material": mat,
                    "price_per_m2": per_m2.get(slug),
                    "is_new": is_new,
                    "size_mode": size_modes.get(slug, "variant"),
                    "tailor": tailors[pi % len(tailors)] if tailors else None,
                },
            )
            product.styles.set([styles[s] for s in style_slugs if s in styles])
            product.rooms.set([rooms[r] for r in room_slugs if r in rooms])
            # Ranglar (M2M) — birinchi 3 tasi.
            product.colors.set(list(colors.values())[:3])
            # Tayyor o'lchamli variantlar — har birining to'liq narxi bilan.
            self._seed_sizes(product, Decimal(price))

    # Tayyor o'lchamli variantlar (S/M/L), har biri o'z narxiga ega. Mavjud bo'sh
    # variantlarni yangilaymiz (orderlar bog'langan bo'lishi mumkin — id saqlanadi), yetmasa yaratamiz.
    def _seed_sizes(self, product, base):
        presets = [
            ("S · 140×240", 140, 240, base),
            ("M · 200×270", 200, 270, base + Decimal("300000")),
            ("L · 260×280", 260, 280, base + Decimal("600000")),
        ]
        existing = list(product.variants.order_by("id"))
        for i, (name, w, h, price) in enumerate(presets):
            if i < len(existing):
                v = existing[i]
                v.name, v.width_cm, v.height_cm, v.price = name, w, h, price
                v.is_active = True
                v.save()
            else:
                ProductVariant.objects.create(
                    product=product, name=name, width_cm=w, height_cm=h, price=price
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

    def _testimonials(self):
        # name, loc_uz, loc_ru, stars, date_uz, date_ru, text_uz, text_ru, initials, color
        data = [
            ("Nodira Karimova", "Toshkent", "Ташкент", 5, "2 oy oldin", "2 месяца назад",
             "Yashash xonasiga velvet parda oldim — hamma ko'rgan kishilar maqtaydi. "
             "Rangi rasmda ko'rsatilgandek, hech qanday farqi yo'q. Yetkazib berish ham tez bo'ldi.",
             "Купила велюровые шторы в гостиную — все, кто приходит, восхищаются. "
             "Цвет точь-в-точь как на фото. Доставка быстрая, всё в порядке.",
             "NK", "#C9A769"),
            ("Sherzod Tursunov", "Farg'ona", "Фергана", 5, "3 oy oldin", "3 месяца назад",
             "O'lchov uchun usta 24 soat ichida keldi, xuddi aytganlaridek. Pardalar aniq kesilgan, "
             "osilgandan keyin juda chiroyli ko'rinadi. Narxi ham adolatli.",
             "Мастер по замеру приехал ровно в течение 24 часов, как и обещали. Шторы скроены точно "
             "по размеру, после установки смотрятся великолепно.",
             "SH", "#6B8F71"),
            ("Malika Yusupova", "Samarqand", "Самарканд", 5, "1 oy oldin", "1 месяц назад",
             "Ikki yildan beri ishlataman — mato cho'zilmagan, rang o'chmagan. Quyosh ko'p tushishiga "
             "qaramasdan sifatini saqlab qolgan. Navbatdagi xonaga ham shu yerdan olaman.",
             "Использую уже два года — ткань не вытянулась, цвет не выгорел. Несмотря на то что солнце "
             "бьёт сильно, качество держится. Следующую комнату тоже куплю здесь.",
             "MY", "#8B6F3A"),
            ("Dilshod Nazarov", "Toshkent, Yunusobod", "Ташкент, Юнусабад", 5, "3 hafta oldin", "3 недели назад",
             "AI yordamchi orqali pardani tanladim — uning tavsiyasi to'g'ri chiqdi. Qo'ng'iroq qilmasdan "
             "ham buyurtma bersa bo'ladi, lekin maslahat so'rasam hamma savolga javob berishdi.",
             "Выбрал шторы через AI-помощника — его рекомендация оказалась точной. Можно заказать без "
             "звонка, но когда спросил совет, на все вопросы ответили.",
             "DN", "#4A6FA5"),
            ("Zulfiya Rashidova", "Andijon", "Андижан", 5, "5 oy oldin", "5 месяцев назад",
             "Bolalar xonasiga sheer parda olishni xohlardim, ammo qaysinisini tanlashni bilmadim. "
             "Maslahat so'raganimda menga mos variantni aniqlab berishdi. Natija a'lo.",
             "Хотела шторы шир для детской, но не знала, какие выбрать. Когда попросила совет, подобрали "
             "подходящий вариант. Результат отличный.",
             "ZR", "#B56576"),
            ("Umida Xoliqova", "Namangan", "Наманган", 5, "6 oy oldin", "6 месяцев назад",
             "Birinchi marta linen parda oluvdim, shubhalanadim. Lekin qo'limga olgach matoning sifatini "
             "bildim. Endi butun uyimga shu yerdan olaman, uchinchi buyurtmam.",
             "Первый раз брала льняные шторы, сомневалась. Но когда взяла в руки — сразу почувствовала "
             "качество ткани. Теперь весь дом одеваю отсюда, это уже третий заказ.",
             "UX", "#7A6FA5"),
        ]
        for i, (name, lu, lr, stars, du, dr, tu, tr, initials, color) in enumerate(data):
            Testimonial.objects.update_or_create(
                sort_order=i,
                defaults={
                    "name": name,
                    "location_uz": lu, "location_ru": lr,
                    "text_uz": tu, "text_ru": tr,
                    "date_label_uz": du, "date_label_ru": dr,
                    "stars": stars, "initials": initials, "color": color,
                },
            )

    def _works(self, rooms):
        # room_slug, tag_uz, tag_ru, is_tall, image_url
        data = [
            ("living", "Velvet · Navy", "Велюр · Тёмно-синий", True,
             "https://images.unsplash.com/photo-1616627561950-9f746e330187?w=900&q=85"),
            ("bedroom", "Linen · Krem", "Лён · Крем", False,
             "https://images.unsplash.com/photo-1540518614846-7eded433c457?w=900&q=85"),
            ("kids", "Sheer · Pearl", "Шир · Жемчуг", False,
             "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=900&q=85"),
            ("bedroom", "Blackout · Camel", "Блэкаут · Кэмел", True,
             "https://images.unsplash.com/photo-1567538096630-e0c55bd6374c?w=900&q=85"),
            ("office", "Velvet · Forest", "Велюр · Лесной", False,
             "https://images.unsplash.com/photo-1556228453-efd6c1ff04f6?w=900&q=85"),
            ("living", "Linen · Stone", "Лён · Стоун", True,
             "https://images.unsplash.com/photo-1493663284031-b7e3aefcae8e?w=900&q=85"),
            ("bedroom", "Silk · Gold", "Шёлк · Золото", False,
             "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?w=900&q=85"),
            ("office", "Blackout · Charcoal", "Блэкаут · Уголь", False,
             "https://images.unsplash.com/photo-1631679706909-1844bbd07221?w=900&q=85"),
            ("kids", "Sheer · White", "Шир · Белый", True,
             "https://images.unsplash.com/photo-1538688525198-9b88f6f53126?w=900&q=85"),
            ("bedroom", "Sheer · Ivory", "Шир · Айвори", False,
             "https://images.unsplash.com/photo-1494438639946-1ebd1d20bf85?w=900&q=85"),
            ("office", "Silk · Cobalt", "Шёлк · Кобальт", False,
             "https://images.unsplash.com/photo-1513161455079-7dc1de15ef3e?w=900&q=85"),
        ]
        # Teg materialiga qarab ishni mos mahsulotga bog'laymiz (detailda ko'rsatiladi).
        product_by_keyword = {
            "Velvet": Product.objects.filter(slug="velvet-shoh").first(),
            "Linen": Product.objects.filter(slug="linen-sahar").first(),
            "Sheer": Product.objects.filter(slug="sheer-nur").first(),
            "Blackout": Product.objects.filter(slug="blackout-noir").first(),
        }
        for i, (room_slug, tu, tr, is_tall, url) in enumerate(data):
            keyword = tu.split(" ")[0]
            work, _ = Work.objects.update_or_create(
                sort_order=i,
                defaults={
                    "room": rooms.get(room_slug),
                    "product": product_by_keyword.get(keyword),
                    "tag_uz": tu, "tag_ru": tr,
                    "is_tall": is_tall,
                },
            )
            if not work.image:
                try:
                    work.image.save(f"work-{i}.jpg", ContentFile(_download(url)), save=True)
                except Exception:
                    pass

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
                    defaults={
                        "rating": rating,
                        "rating_tailor": rating,
                        "rating_service": min(5, rating + 1) if rating < 5 else 5,
                        "comment": text,
                        "is_published": True,
                    },
                )
            agg = product.reviews.filter(is_published=True).aggregate(a=Avg("rating"))["a"] or 0
            product.rating_avg = round(Decimal(agg), 2)
            product.save(update_fields=["rating_avg"])

    # ------------------------------------------------------------------
    # Dashboard demo data (orders, customers, payments, measurements...)
    # ------------------------------------------------------------------

    def _ensure_product_assets(self, colors):
        """Guarantee every product has a variant + a main image row."""
        palette = list(colors.values()) or list(Color.objects.all())
        for product in Product.objects.all():
            if not product.variants.exists():
                ProductVariant.objects.create(
                    product=product, name="Standart · 200×270", width_cm=200, height_cm=270,
                    price=Decimal("500000"),
                )
            if not product.colors.exists() and palette:
                product.colors.set(palette[:3])
            if not product.images.exists():
                # Lightweight placeholder image row so the dashboard has thumbnails.
                img = ProductImage(product=product, is_main=True, sort_order=0)
                img.image.save(
                    f"demo-{product.slug}.png",
                    ContentFile(_PLACEHOLDER_PNG),
                    save=True,
                )

    def _customers(self):
        User = get_user_model()
        names = [
            "Aziz Karimov", "Nigora Sobirova", "Bekzod Tursunov", "Kamola Yusupova",
            "Sherzod Aliyev", "Madina Rustamova", "Ilhom Qodirov", "Zarina Hamidova",
            "Otabek Nazarov", "Sevara Tojiyeva", "Jahongir Umarov", "Dilfuza Salimova",
            "Rustam Ergashev", "Gulnoza Mirzaeva", "Akmal Yo'ldoshev",
        ]
        now = timezone.now()
        customers = []
        for i, name in enumerate(names):
            phone = f"{DEMO_PHONE_PREFIX}{1000000 + i:07d}"[:13]
            joined = now - timedelta(days=random.randint(0, 40), hours=random.randint(0, 23))
            user, created = User.objects.get_or_create(
                phone=phone,
                defaults={
                    "full_name": name,
                    "role": "customer",
                    "is_phone_verified": True,
                    "date_joined": joined,
                },
            )
            if created:
                # date_joined has a default, so force it onto the spread window.
                User.objects.filter(pk=user.pk).update(date_joined=joined)
            customers.append(user)
            Address.objects.get_or_create(
                user=user,
                city="Toshkent",
                street="Amir Temur",
                home=str(10 + i),
                defaults={"region": "Toshkent", "is_default": True},
            )
        return customers

    def _orders(self, customers):
        if not customers:
            return []
        variants = list(ProductVariant.objects.select_related("product"))
        if not variants:
            return []

        now = timezone.now()
        statuses = (
            ["completed"] * 6
            + ["paid"] * 4
            + ["processing"] * 3
            + ["shipped"] * 2
            + ["measuring", "sewing", "pending", "cancelled"]
        )
        orders = []
        # Continue numbering after any existing demo orders so re-running
        # (without --flush) appends rather than colliding on order_number.
        existing = (
            Order.objects.filter(order_number__startswith="ZZ-DEMO-")
            .order_by("-order_number")
            .first()
        )
        start_seq = int(existing.order_number.split("-")[-1]) if existing else 0
        for i in range(40):
            n = start_seq + i + 1
            user = random.choice(customers)
            status = random.choice(statuses)
            paid = status in ("completed", "paid", "shipped", "processing", "measuring", "sewing")
            payment_status = "paid" if paid else ("failed" if status == "cancelled" and random.random() < 0.3 else "unpaid")
            provider = random.choice(["payme", "click"]) if paid else ""
            created = now - timedelta(days=random.randint(0, 29), hours=random.randint(0, 23))

            order = Order.objects.create(
                order_number=f"ZZ-DEMO-{n:04d}",
                user=user,
                status=status,
                payment_status=payment_status,
                payment_provider=provider,
                comment=random.choice(["", "", "Tezroq yetkazib bering", "Eshik oldiga qoldiring"]),
            )
            # Backdate created_at (auto_now_add ignores the constructor value).
            Order.objects.filter(pk=order.pk).update(created_at=created)
            order.created_at = created

            subtotal = Decimal("0")
            chosen = random.sample(variants, k=min(random.randint(1, 3), len(variants)))
            for v in chosen:
                qty = random.randint(1, 3)
                unit = Decimal(random.randint(150000, 2500000))
                line = unit * qty
                subtotal += line
                OrderItem.objects.create(
                    order=order,
                    variant=v,
                    product_name_snapshot=v.product.name or v.product.slug,
                    unit_price=unit,
                    quantity=qty,
                    line_total=line,
                )
            delivery = Decimal(random.choice([0, 0, 30000, 50000]))
            discount = Decimal(random.choice([0, 0, 0, 50000, 100000]))
            total = subtotal - discount + delivery
            Order.objects.filter(pk=order.pk).update(
                subtotal=subtotal, discount=discount, delivery_fee=delivery, total=total
            )
            order.subtotal, order.discount, order.delivery_fee, order.total = (
                subtotal, discount, delivery, total,
            )

            if payment_status == "paid" and provider:
                Payment.objects.get_or_create(
                    provider=provider,
                    provider_transaction_id=f"demo-{order.order_number}",
                    defaults={
                        "order": order,
                        "amount": total,
                        "state": Payment.STATE_COMPLETED,
                        "paid_at": created,
                    },
                )
            orders.append(order)
        return orders

    def _measurements(self, customers):
        if not customers:
            return
        now = timezone.now()
        slots = ["09:00-12:00", "12:00-15:00", "15:00-18:00", "18:00-21:00"]
        statuses = ["requested"] * 4 + ["scheduled", "scheduled", "done", "cancelled"]
        for i in range(8):
            user = random.choice(customers)
            address = user.addresses.first()
            if not address:
                continue
            MeasurementRequest.objects.create(
                user=user,
                address=address,
                preferred_date=(now + timedelta(days=random.randint(-5, 10))).date(),
                time_slot=random.choice(slots),
                status=statuses[i],
                note=random.choice(["", "Mehmonxona uchun", "2 ta deraza"]),
            )

    def _extra_reviews(self, customers):
        """Add unpublished (pending moderation) reviews to round out the mix."""
        if not customers:
            return
        products = list(Product.objects.all())
        comments = [
            "Mahsulot kelganini kutyapman, lekin ko'rinishi yaxshi.",
            "Narxi biroz qimmat, ammo sifati arziydi.",
            "Yetkazib berish biroz kechikdi.",
            "Rangi rasmga mos, lekin matosi yupqaroq.",
            "Umuman olganda qoniqdim.",
        ]
        for product in products:
            sample = random.sample(customers, k=min(random.randint(2, 4), len(customers)))
            for user in sample:
                Review.objects.get_or_create(
                    product=product,
                    user=user,
                    defaults={
                        "rating": random.randint(3, 5),
                        "rating_tailor": random.randint(3, 5),
                        "rating_service": random.randint(3, 5),
                        "comment": random.choice(comments),
                        "is_published": random.random() < 0.4,
                    },
                )

# 1x1 transparent PNG used as a placeholder product thumbnail.
_PLACEHOLDER_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc````"
    b"\x00\x00\x00\x05\x00\x01\xa5\xf6E@\x00\x00\x00\x00IEND\xaeB`\x82"
)
