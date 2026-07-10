from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class Notification(BaseModel):
    """Sayt-ichi (dashboard) bildirishnoma — bitta qatorlik voqea.

    ``kind`` erkin satr (masalan 'order_new', 'order_status') — front shu bo'yicha
    ikonka/rang tanlaydi. Telegram/SMS kanallariga yuborish alohida (services.py,
    celery task) — bu model faqat saytdagi "qo'ng'iroq" ro'yxati uchun.
    """

    KIND_ORDER_NEW = "order_new"
    KIND_ORDER_STATUS = "order_status"
    KIND_CHOICES = (
        (KIND_ORDER_NEW, "Yangi buyurtma"),
        (KIND_ORDER_STATUS, "Buyurtma holati o'zgardi"),
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField(max_length=32, choices=KIND_CHOICES, default=KIND_ORDER_NEW)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True, default="")
    order = models.ForeignKey(
        "orders.Order", on_delete=models.SET_NULL, null=True, blank=True, related_name="notifications"
    )
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read", "-created_at"])]

    def __str__(self):
        return f"{self.recipient_id}:{self.kind}:{self.title}"
