from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = ("provider", "provider_transaction_id", "order", "amount", "state", "paid_at")
    list_filter = ("provider", "state")
    search_fields = ("provider_transaction_id", "order__order_number")
    readonly_fields = [f.name for f in Payment._meta.fields]

    def has_add_permission(self, request):
        return False
