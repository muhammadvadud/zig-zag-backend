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


class Product(BaseModel):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=150, default="")
    description = models.TextField(blank=True, default="")
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
    title = models.CharField(max_length=150, default="")
    image = models.ImageField(upload_to="collections/", null=True, blank=True)
    products = models.ManyToManyField(Product, blank=True, related_name="collections")
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order"]


class Banner(BaseModel):
    title = models.CharField(max_length=150, blank=True, default="")
    image = models.ImageField(upload_to="banners/")
    link = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order"]


class FAQ(BaseModel):
    question = models.CharField(max_length=255, default="")
    answer = models.TextField(default="")
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order"]
        verbose_name = "FAQ"
