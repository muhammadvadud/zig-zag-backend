from django.db import models

from apps.common.models import BaseModel


class ServiceTariff(BaseModel):
    """Smart / Lux / Premium service plans (consulting, sewing, AI, etc.)."""

    code = models.CharField(max_length=32, unique=True)
    name_uz = models.CharField(max_length=100)
    name_ru = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    price_per_m2 = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_popular = models.BooleanField(default=False)
    features = models.JSONField(default=dict, blank=True)
    ai_chat_enabled = models.BooleanField(default=False)
    ai_image_enabled = models.BooleanField(default=False)
    ai_monthly_token_limit = models.PositiveIntegerField(null=True, blank=True)
    ai_image_monthly_limit = models.PositiveIntegerField(null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "price"]

    def __str__(self):
        return self.code

    def name(self, lang="uz"):
        return self.name_ru if lang == "ru" else self.name_uz

    def features_for(self, lang="uz"):
        if isinstance(self.features, dict):
            return self.features.get(lang, self.features.get("uz", []))
        return self.features or []
