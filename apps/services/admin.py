from django.contrib import admin

from .models import ServiceTariff


@admin.register(ServiceTariff)
class ServiceTariffAdmin(admin.ModelAdmin):
    list_display = ("code", "name_uz", "price", "is_popular", "ai_chat_enabled", "ai_image_enabled", "is_active")
    list_filter = ("is_popular", "ai_chat_enabled", "ai_image_enabled", "is_active")
    search_fields = ("code", "name_uz", "name_ru")
