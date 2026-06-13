from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import Cart, CartItem


class CartItemInline(TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(ModelAdmin):
    list_display = ("id", "user", "session_key", "created_at")
    search_fields = ("user__phone", "session_key")
    inlines = [CartItemInline]


@admin.register(CartItem)
class CartItemAdmin(ModelAdmin):
    list_display = ("cart", "variant", "quantity", "service_tariff")
    search_fields = ("variant__sku",)
