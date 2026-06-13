from django.db import models

from apps.common.models import BaseModel


class ServiceTariff(BaseModel):
    """Smart / Lux / Premium service plans (consulting, sewing, AI, etc.)."""

    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=100, default="")
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    price_per_m2 = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_popular = models.BooleanField(default=False)
    features = models.JSONField(default=list, blank=True)
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
