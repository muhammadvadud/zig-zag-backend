from django.contrib import admin
from modeltranslation.admin import TranslationAdmin
from unfold.admin import ModelAdmin, TabularInline

from .ratings import recompute_product_rating

from .models import (
    FAQ,
    Banner,
    Category,
    Collection,
    Color,
    Favorite,
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


class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(TabularInline):
    model = ProductVariant
    extra = 1


@admin.register(Category)
class CategoryAdmin(TranslationAdmin, ModelAdmin):
    list_display = ("slug", "name_uz", "sort_order", "is_active")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name_uz",)}


@admin.register(Color)
class ColorAdmin(TranslationAdmin, ModelAdmin):
    list_display = ("name_uz", "name_ru", "hex")
    search_fields = ("name_uz", "name_ru")


@admin.register(Style)
class StyleAdmin(TranslationAdmin, ModelAdmin):
    list_display = ("slug", "name_uz", "sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("slug", "name_uz", "name_ru")
    prepopulated_fields = {"slug": ("name_uz",)}


@admin.register(Room)
class RoomAdmin(TranslationAdmin, ModelAdmin):
    list_display = ("slug", "name_uz", "sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("slug", "name_uz", "name_ru")
    prepopulated_fields = {"slug": ("name_uz",)}


@admin.register(Tailor)
class TailorAdmin(TranslationAdmin, ModelAdmin):
    list_display = ("name_uz", "specialty_uz", "rating", "orders_count", "sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name_uz", "name_ru", "specialty_uz")


@admin.register(Product)
class ProductAdmin(TranslationAdmin, ModelAdmin):
    list_display = ("slug", "name_uz", "category", "tailor", "base_price", "discount_percent", "stock", "is_new", "custom_only", "is_active")
    list_filter = ("category", "tailor", "is_new", "custom_only", "is_active")
    search_fields = ("slug", "name_uz", "name_ru")
    autocomplete_fields = ("tailor",)
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
    list_display = (
        "product",
        "user",
        "rating",
        "rating_tailor",
        "rating_service",
        "is_published",
        "created_at",
    )
    list_filter = ("is_published", "rating", "rating_tailor", "rating_service")
    search_fields = ("product__name_uz", "user__phone")
    actions = ["publish"]

    @admin.action(description="Tanlangan sharhlarni e'lon qilish")
    def publish(self, request, queryset):
        # .update() signal'larni chetlab o'tadi, shuning uchun baholarni qo'lda
        # qayta hisoblaymiz (mahsulot + bog'liq chevar).
        products = {r.product for r in queryset.select_related("product__tailor")}
        queryset.update(is_published=True)
        for product in products:
            recompute_product_rating(product)


@admin.register(Favorite)
class FavoriteAdmin(ModelAdmin):
    list_display = ("user", "product", "created_at")
    search_fields = ("user__phone", "product__name_uz")


@admin.register(Collection)
class CollectionAdmin(TranslationAdmin, ModelAdmin):
    list_display = ("slug", "title_uz", "sort_order", "is_active")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("title_uz",)}
    filter_horizontal = ("products",)


@admin.register(Banner)
class BannerAdmin(TranslationAdmin, ModelAdmin):
    list_display = ("title_uz", "sort_order", "is_active")
    list_filter = ("is_active",)


@admin.register(FAQ)
class FAQAdmin(TranslationAdmin, ModelAdmin):
    list_display = ("question_uz", "sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("question_uz", "question_ru")


@admin.register(HeroContent)
class HeroContentAdmin(TranslationAdmin, ModelAdmin):
    list_display = ("title_uz", "sort_order", "is_active")
    list_filter = ("is_active",)


@admin.register(Testimonial)
class TestimonialAdmin(TranslationAdmin, ModelAdmin):
    list_display = ("name", "location_uz", "stars", "sort_order", "is_active")
    list_filter = ("is_active", "stars")
    search_fields = ("name", "location_uz", "location_ru")


@admin.register(Work)
class WorkAdmin(TranslationAdmin, ModelAdmin):
    list_display = ("__str__", "product", "room", "tag_uz", "is_tall", "sort_order", "is_active")
    list_filter = ("is_active", "is_tall", "room", "product")
    autocomplete_fields = ("product",)
