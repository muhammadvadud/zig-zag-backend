from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class Cart(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cart",
    )
    session_key = models.CharField(max_length=64, null=True, blank=True, db_index=True)

    def __str__(self):
        return f"Cart#{self.pk}"

    @property
    def subtotal(self):
        return sum((item.line_total for item in self.items.all()), Decimal("0"))

    @property
    def total(self):
        return self.subtotal


class CartItem(BaseModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey("catalog.ProductVariant", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    width_cm = models.PositiveIntegerField(null=True, blank=True)
    height_cm = models.PositiveIntegerField(null=True, blank=True)
    service_tariff = models.ForeignKey(
        "services.ServiceTariff", on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ["created_at"]

    @property
    def area_m2(self):
        if self.width_cm and self.height_cm:
            return (Decimal(self.width_cm) / 100) * (Decimal(self.height_cm) / 100)
        return Decimal("0")

    @property
    def unit_price(self):
        return self.variant.unit_price

    @property
    def service_cost(self):
        tariff = self.service_tariff
        if tariff and tariff.price_per_m2 and self.area_m2:
            return (tariff.price_per_m2 * self.area_m2).quantize(Decimal("1"))
        if tariff:
            return tariff.price
        return Decimal("0")

    @property
    def line_total(self):
        return (self.unit_price + self.service_cost) * self.quantity
