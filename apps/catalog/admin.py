from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import (
    FAQ,
    Banner,
    Category,
    Collection,
    Color,
    Favorite,
    Product,
    ProductImage,
    ProductVariant,
    Review,
)


class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(TabularInline):
    model = ProductVariant
    extra = 1


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("slug", "name_uz", "sort_order", "is_active")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name_uz",)}


@admin.register(Color)
class ColorAdmin(ModelAdmin):
    list_display = ("name_uz", "name_ru", "hex")
    search_fields = ("name_uz", "name_ru")


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ("slug", "name_uz", "category", "base_price", "discount_percent", "stock", "is_new", "is_active")
    list_filter = ("category", "is_new", "is_active")
    search_fields = ("slug", "name_uz", "name_ru")
    prepopulated_fields = {"slug": ("name_uz",)}
    inlines = [ProductVariantInline, ProductImageInline]


@admin.register(ProductVariant)
class ProductVariantAdmin(ModelAdmin):
    list_display = ("sku", "product", "color", "stock", "extra_price")
    search_fields = ("sku", "product__name_uz")
    list_filter = ("color",)


@admin.register(ProductImage)
class ProductImageAdmin(ModelAdmin):
    list_display = ("product", "variant", "is_main", "sort_order")
    list_filter = ("is_main",)


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ("product", "user", "rating", "is_published", "created_at")
    list_filter = ("is_published", "rating")
    search_fields = ("product__name_uz", "user__phone")
    actions = ["publish"]

    @admin.action(description="Tanlangan sharhlarni e'lon qilish")
    def publish(self, request, queryset):
        queryset.update(is_published=True)


@admin.register(Favorite)
class FavoriteAdmin(ModelAdmin):
    list_display = ("user", "product", "created_at")
    search_fields = ("user__phone", "product__name_uz")


@admin.register(Collection)
class CollectionAdmin(ModelAdmin):
    list_display = ("slug", "title_uz", "sort_order", "is_active")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("title_uz",)}
    filter_horizontal = ("products",)


@admin.register(Banner)
class BannerAdmin(ModelAdmin):
    list_display = ("title_uz", "sort_order", "is_active")
    list_filter = ("is_active",)


@admin.register(FAQ)
class FAQAdmin(ModelAdmin):
    list_display = ("question_uz", "sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("question_uz", "question_ru")
