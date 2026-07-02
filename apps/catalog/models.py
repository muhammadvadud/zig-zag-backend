from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class Category(BaseModel):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100, default="")
    icon = models.ImageField(upload_to="categories/icons/", null=True, blank=True)
    image = models.ImageField(upload_to="categories/", null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.slug


class Color(BaseModel):
    name = models.CharField(max_length=64, default="")
    hex = models.CharField(max_length=7)

    def __str__(self):
        return f"{self.name} ({self.hex})"


class Style(BaseModel):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100, default="")
    blurb = models.CharField(max_length=255, blank=True, default="")
    image = models.ImageField(upload_to="styles/", null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.slug


class Room(BaseModel):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100, default="")
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.slug


class Tailor(BaseModel):
    """Chevar usta — mahsulotni tikuvchi (mahsulotga biriktiriladi)."""

    name = models.CharField(max_length=120, default="")
    initials = models.CharField(max_length=4, blank=True, default="")
    specialty = models.CharField(max_length=120, blank=True, default="")
    photo = models.ImageField(upload_to="tailors/", null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    orders_count = models.PositiveIntegerField(default=0)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Badge(BaseModel):
    """Mahsulotga biriktiriladigan nishon (masalan: Yangi, Chegirma, Top).

    Bir mahsulotga bir nechta nishon biriktirilishi mumkin. Har bir nishon
    o'z rangiga ega."""

    name = models.CharField(max_length=64, default="")
    color = models.CharField(max_length=7, default="#c9a769")  # HEX rang
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name


class Product(BaseModel):
    SIZE_MODE_VARIANT = "variant"
    SIZE_MODE_CUSTOM = "custom"
    SIZE_MODE_BOTH = "both"
    SIZE_MODE_CHOICES = [
        (SIZE_MODE_VARIANT, "Tayyor o'lchamlar (variant)"),
        (SIZE_MODE_CUSTOM, "Faqat mijoz o'lchami (custom)"),
        (SIZE_MODE_BOTH, "Ikkalasi ham"),
    ]

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=150, default="")
    description = models.TextField(blank=True, default="")
    material = models.CharField(max_length=64, blank=True)
    # Narx endi variantlarda (tayyor o'lchamlar) va per-m² da (custom) — alohida "asosiy narx" yo'q.
    price_per_m2 = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  # custom o'lcham narxi (1 m²)
    discount_percent = models.PositiveIntegerField(default=0)
    is_new = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    size_mode = models.CharField(max_length=8, choices=SIZE_MODE_CHOICES, default=SIZE_MODE_VARIANT)
    custom_only = models.BooleanField(default=False)  # faqat o'lchov bo'yicha tikiladi (standart o'lcham yo'q) — size_mode dan hosila
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    views_count = models.PositiveIntegerField(default=0)
    styles = models.ManyToManyField("Style", blank=True, related_name="products")
    rooms = models.ManyToManyField("Room", blank=True, related_name="products")
    colors = models.ManyToManyField("Color", blank=True, related_name="products")
    badges = models.ManyToManyField("Badge", blank=True, related_name="products")
    tailor = models.ForeignKey(
        "Tailor", on_delete=models.SET_NULL, null=True, blank=True, related_name="products"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["is_new"]),
        ]

    def __str__(self):
        return self.slug

    def save(self, *args, **kwargs):
        # custom_only ni size_mode bilan sinxronlaymiz (mijozlar saytidagi eski mantiq shu boolean ga tayanadi).
        self.custom_only = self.size_mode == self.SIZE_MODE_CUSTOM
        super().save(*args, **kwargs)

    def apply_discount(self, amount):
        """Berilgan summaga mahsulot chegirmasini qo'llaydi (butun so'mga yaxlitlab)."""
        amount = Decimal(amount or 0)
        if self.discount_percent:
            amount = amount * Decimal(100 - self.discount_percent) / Decimal(100)
        return amount.quantize(Decimal("1"))

    @property
    def starting_price(self):
        """Eng arzon faol variant narxi (chegirmasiz) — "dan" narxi / eski narx uchun."""
        prices = [v.price for v in self.variants.all() if v.is_active]
        return min(prices) if prices else Decimal("0")

    @property
    def final_price(self):
        """Kartada ko'rsatiladigan narx — eng arzon variant, chegirma bilan."""
        return self.apply_discount(self.starting_price)


class ProductVariant(BaseModel):
    """Tayyor o'lchamli variant: mahsulotning belgilangan eni × bo'yi (sm) va narxi."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    name = models.CharField(max_length=120, blank=True, default="")  # masalan "150×250 sm"
    width_cm = models.DecimalField(max_digits=7, decimal_places=1, null=True, blank=True)
    height_cm = models.DecimalField(max_digits=7, decimal_places=1, null=True, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # shu o'lchamning to'liq narxi (chegirmasiz)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["price", "width_cm", "height_cm", "id"]

    def __str__(self):
        if self.name:
            return self.name
        if self.width_cm and self.height_cm:
            return f"{self.width_cm}×{self.height_cm} sm"
        return f"Variant #{self.pk}"

    @property
    def unit_price(self):
        """Variant narxi (mahsulot chegirmasi bilan)."""
        return self.product.apply_discount(self.price)


class ProductImage(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    color = models.ForeignKey(
        "Color", on_delete=models.SET_NULL, null=True, blank=True, related_name="images"
    )
    image = models.ImageField(upload_to="products/")
    is_main = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-is_main", "sort_order"]


class Review(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    order = models.ForeignKey(
        "orders.Order", on_delete=models.SET_NULL, null=True, blank=True, related_name="reviews"
    )
    # Uchta alohida baho: mahsulot, chevar (usta), xizmat uchun (har biri 1-5).
    rating = models.PositiveSmallIntegerField()  # mahsulot bahosi
    rating_tailor = models.PositiveSmallIntegerField(default=0)  # chevar bahosi
    rating_service = models.PositiveSmallIntegerField(default=0)  # xizmat bahosi
    comment = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("product", "user")

    def __str__(self):
        return f"{self.product_id} - {self.rating}"


class Favorite(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="favorited_by")

    class Meta:
        unique_together = ("user", "product")
        ordering = ["-created_at"]


class Collection(BaseModel):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=150, default="")
    image = models.ImageField(upload_to="collections/", null=True, blank=True)
    products = models.ManyToManyField(Product, blank=True, related_name="collections")
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order"]


class Banner(BaseModel):
    title = models.CharField(max_length=150, blank=True, default="")
    eyebrow = models.CharField(max_length=100, blank=True, default="")
    subtitle = models.CharField(max_length=255, blank=True, default="")
    cta = models.CharField(max_length=64, blank=True, default="")
    image = models.ImageField(upload_to="banners/")
    link = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order"]


class HeroContent(BaseModel):
    """Bosh sahifa hero blokidagi (banner oldidagi) matnlar — bitta faol yozuv."""

    eyebrow = models.CharField(max_length=120, blank=True, default="")
    title = models.CharField(max_length=180, blank=True, default="")
    title_italic = models.CharField(max_length=120, blank=True, default="")
    description = models.CharField(max_length=400, blank=True, default="")
    stat1_value = models.CharField(max_length=40, blank=True, default="")
    stat1_label = models.CharField(max_length=60, blank=True, default="")
    stat2_value = models.CharField(max_length=40, blank=True, default="")
    stat2_label = models.CharField(max_length=60, blank=True, default="")
    stat3_value = models.CharField(max_length=40, blank=True, default="")
    stat3_label = models.CharField(max_length=60, blank=True, default="")
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order"]
        verbose_name = "Hero content"
        verbose_name_plural = "Hero content"

    def __str__(self):
        return self.title or f"Hero #{self.pk}"


class FAQ(BaseModel):
    question = models.CharField(max_length=255, default="")
    answer = models.TextField(default="")
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order"]
        verbose_name = "FAQ"


class Testimonial(BaseModel):
    """Bosh sahifadagi mijozlar fikri (sharh kartalari)."""

    name = models.CharField(max_length=120, default="")
    location = models.CharField(max_length=120, blank=True, default="")
    text = models.TextField(default="")
    date_label = models.CharField(max_length=60, blank=True, default="")
    stars = models.PositiveSmallIntegerField(default=5)
    initials = models.CharField(max_length=4, blank=True, default="")
    color = models.CharField(max_length=7, blank=True, default="#C9A769")
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "-created_at"]

    def __str__(self):
        return self.name or f"Testimonial #{self.pk}"


class Work(BaseModel):
    """Amalga oshirilgan loyihalar galereyasi (portfolio)."""

    room = models.ForeignKey(
        Room, on_delete=models.SET_NULL, null=True, blank=True, related_name="works"
    )
    product = models.ForeignKey(
        "Product", on_delete=models.SET_NULL, null=True, blank=True, related_name="works"
    )
    tag = models.CharField(max_length=120, blank=True, default="")
    image = models.ImageField(upload_to="works/")
    is_tall = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "-created_at"]

    def __str__(self):
        return f"Work #{self.pk}"
