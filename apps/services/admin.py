from django.contrib import admin
from modeltranslation.admin import TranslationAdmin
from unfold.admin import ModelAdmin

from .models import ServiceTariff


@admin.register(ServiceTariff)
class ServiceTariffAdmin(TranslationAdmin, ModelAdmin):
    list_display = ("code", "name_uz", "price", "is_popular", "is_active")
    list_filter = ("is_popular", "is_active")
    search_fields = ("code", "name_uz", "name_ru")
