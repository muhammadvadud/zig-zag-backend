from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import GiftCard, MeasurementRequest, Order, OrderItem


class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("variant", "product_name_snapshot", "unit_price", "quantity", "line_total")


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ("order_number", "user", "status", "payment_status", "total", "created_at")
    list_filter = ("status", "payment_status", "payment_provider")
    search_fields = ("order_number", "user__phone")
    inlines = [OrderItemInline]
    readonly_fields = ("order_number", "subtotal", "total")


@admin.register(OrderItem)
class OrderItemAdmin(ModelAdmin):
    list_display = ("order", "product_name_snapshot", "unit_price", "quantity", "line_total")
    search_fields = ("order__order_number", "product_name_snapshot")


@admin.register(MeasurementRequest)
class MeasurementAdmin(ModelAdmin):
    list_display = ("user", "preferred_date", "time_slot", "status")
    list_filter = ("status",)
    search_fields = ("user__phone",)


@admin.register(GiftCard)
class GiftCardAdmin(ModelAdmin):
    list_display = ("code", "balance", "owner", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code",)
