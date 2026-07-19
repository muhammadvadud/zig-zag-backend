from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class Order(BaseModel):
    STATUS_CHOICES = (
        ("pending", "pending"),
        ("paid", "paid"),
        ("processing", "processing"),
        ("measuring", "measuring"),
        ("sewing", "sewing"),
        ("shipped", "shipped"),
        ("completed", "completed"),
        ("cancelled", "cancelled"),
        ("refunded", "refunded"),
    )
    PAYMENT_STATUS_CHOICES = (
        ("unpaid", "unpaid"),
        ("paid", "paid"),
        ("failed", "failed"),
        ("refunded", "refunded"),
    )
    DELIVERY_METHOD_CHOICES = (
        ("postal", "postal"),
        ("pickup", "pickup"),
    )

    order_number = models.CharField(max_length=32, unique=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending")
    address = models.ForeignKey(
        "accounts.Address", on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    delivery_method = models.CharField(
        max_length=16, choices=DELIVERY_METHOD_CHOICES, default="postal"
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=16, choices=PAYMENT_STATUS_CHOICES, default="unpaid")
    payment_provider = models.CharField(max_length=16, blank=True)
    viewed_order = models.BooleanField(default=False)
    comment = models.TextField(blank=True)
    recipient_full_name = models.CharField(max_length=150, blank=True)
    recipient_phone = models.CharField(max_length=20, blank=True)
    service_tariff = models.ForeignKey(
        "services.ServiceTariff", on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.order_number


class OrderItem(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey("catalog.ProductVariant", on_delete=models.PROTECT)
    color = models.ForeignKey(
        "catalog.Color", on_delete=models.SET_NULL, null=True, blank=True
    )
    product_name_snapshot = models.CharField(max_length=200)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    width_cm = models.PositiveIntegerField(null=True, blank=True)
    height_cm = models.PositiveIntegerField(null=True, blank=True)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.order_id}:{self.product_name_snapshot}"


class MeasurementRequest(BaseModel):
    STATUS_CHOICES = (
        ("requested", "requested"),
        ("scheduled", "scheduled"),
        ("done", "done"),
        ("cancelled", "cancelled"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="measurements")
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="measurements")
    address = models.ForeignKey("accounts.Address", on_delete=models.PROTECT)
    preferred_date = models.DateField()
    time_slot = models.CharField(max_length=32)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="requested")
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]


class GiftCard(BaseModel):
    code = models.CharField(max_length=32, unique=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="gift_cards"
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code
