from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class Category(BaseModel):
    slug = models.SlugField(unique=True)
    name_uz = models.CharField(max_length=100)
    name_ru = models.CharField(max_length=100)
    icon = models.ImageField(upload_to="categories/icons/", null=True, blank=True)
    image = models.ImageField(upload_to="categories/", null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name_uz"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.slug

    def name(self, lang="uz"):
        return self.name_ru if lang == "ru" else self.name_uz


class Color(BaseModel):
    name_uz = models.CharField(max_length=64)
    name_ru = models.CharField(max_length=64)
    hex = models.CharField(max_length=7)

    def __str__(self):
        return f"{self.name_uz} ({self.hex})"

    def name(self, lang="uz"):
        return self.name_ru if lang == "ru" else self.name_uz


class Product(BaseModel):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    slug = models.SlugField(unique=True)
    name_uz = models.CharField(max_length=150)
    name_ru = models.CharField(max_length=150)
    description_uz = models.TextField(blank=True)
    description_ru = models.TextField(blank=True)
    material = models.CharField(max_length=64, blank=True)
    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    price_per_m2 = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    discount_percent = models.PositiveIntegerField(default=0)
    is_new = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    stock = models.PositiveIntegerField(default=0)
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    views_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["is_new"]),
        ]

    def __str__(self):
        return self.slug

    def name(self, lang="uz"):
        return self.name_ru if lang == "ru" else self.name_uz

    def description(self, lang="uz"):
        return self.description_ru if lang == "ru" else self.description_uz

    @property
    def final_price(self):
        if self.discount_percent:
            factor = Decimal(100 - self.discount_percent) / Decimal(100)
            return (self.base_price * factor).quantize(Decimal("1"))
        return self.base_price


class ProductVariant(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    color = models.ForeignKey(Color, on_delete=models.PROTECT, related_name="variants")
    sku = models.CharField(max_length=64, unique=True)
    stock = models.PositiveIntegerField(default=0)
    extra_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]
        unique_together = ("product", "color")

    def __str__(self):
        return self.sku

    @property
    def unit_price(self):
        return self.product.final_price + self.extra_price


class ProductImage(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, null=True, blank=True, related_name="images"
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
    rating = models.PositiveSmallIntegerField()
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
    title_uz = models.CharField(max_length=150)
    title_ru = models.CharField(max_length=150)
    image = models.ImageField(upload_to="collections/", null=True, blank=True)
    products = models.ManyToManyField(Product, blank=True, related_name="collections")
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order"]

    def title(self, lang="uz"):
        return self.title_ru if lang == "ru" else self.title_uz


class Banner(BaseModel):
    title_uz = models.CharField(max_length=150, blank=True)
    title_ru = models.CharField(max_length=150, blank=True)
    image = models.ImageField(upload_to="banners/")
    link = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order"]

    def title(self, lang="uz"):
        return self.title_ru if lang == "ru" else self.title_uz


class FAQ(BaseModel):
    question_uz = models.CharField(max_length=255)
    question_ru = models.CharField(max_length=255)
    answer_uz = models.TextField()
    answer_ru = models.TextField()
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order"]
        verbose_name = "FAQ"
