from django.contrib import admin

from .models import GiftCard, MeasurementRequest, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("variant", "product_name_snapshot", "unit_price", "quantity", "line_total")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "user", "status", "payment_status", "total", "created_at")
    list_filter = ("status", "payment_status", "payment_provider")
    search_fields = ("order_number", "user__phone")
    inlines = [OrderItemInline]
    readonly_fields = ("order_number", "subtotal", "total")


@admin.register(MeasurementRequest)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ("user", "preferred_date", "time_slot", "status")
    list_filter = ("status",)


@admin.register(GiftCard)
class GiftCardAdmin(admin.ModelAdmin):
    list_display = ("code", "balance", "owner", "is_active")
    search_fields = ("code",)
