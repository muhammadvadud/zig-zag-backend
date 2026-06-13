from django.db import models

from apps.common.models import BaseModel


class Payment(BaseModel):
    PROVIDER_CHOICES = (("payme", "payme"), ("click", "click"))

    # Payme transaction states (see merchant API spec).
    STATE_CREATED = 1
    STATE_COMPLETED = 2
    STATE_CANCELLED = -1
    STATE_CANCELLED_AFTER_COMPLETE = -2

    order = models.ForeignKey("orders.Order", on_delete=models.PROTECT, related_name="payments")
    provider = models.CharField(max_length=16, choices=PROVIDER_CHOICES)
    provider_transaction_id = models.CharField(max_length=128, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    state = models.IntegerField(default=STATE_CREATED)
    raw_payload = models.JSONField(default=dict, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_transaction_id"],
                name="uniq_provider_txn",
            )
        ]

    def __str__(self):
        return f"{self.provider}:{self.provider_transaction_id}"
