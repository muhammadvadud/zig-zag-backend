from django.contrib import admin

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


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("slug", "name_uz", "sort_order", "is_active")
    prepopulated_fields = {"slug": ("name_uz",)}


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ("name_uz", "name_ru", "hex")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("slug", "name_uz", "category", "base_price", "discount_percent", "stock", "is_new", "is_active")
    list_filter = ("category", "is_new", "is_active")
    search_fields = ("slug", "name_uz", "name_ru")
    prepopulated_fields = {"slug": ("name_uz",)}
    inlines = [ProductVariantInline, ProductImageInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "is_published", "created_at")
    list_filter = ("is_published", "rating")
    actions = ["publish"]

    @admin.action(description="Tanlangan sharhlarni e'lon qilish")
    def publish(self, request, queryset):
        queryset.update(is_published=True)


admin.site.register(Favorite)
admin.site.register(Collection)
admin.site.register(Banner)
admin.site.register(FAQ)
