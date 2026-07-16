"""24 soat ichida to'lanmagan buyurtmalarni avtomatik bekor qiladi."""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.notifications.services import notify_status_change

from .models import Order
from .services import can_transition

logger = logging.getLogger(__name__)

PAYMENT_TIMEOUT_HOURS = 24


@shared_task(ignore_result=True)
def cancel_unpaid_orders():
    cutoff = timezone.now() - timedelta(hours=PAYMENT_TIMEOUT_HOURS)
    stale = Order.objects.filter(
        status="pending", payment_status="unpaid", created_at__lt=cutoff
    )
    cancelled = 0
    for order in stale:
        if not can_transition(order.status, "cancelled"):
            continue
        order.status = "cancelled"
        order.save(update_fields=["status", "updated_at"])
        notify_status_change(order, "pending", "cancelled")
        cancelled += 1
    if cancelled:
        logger.info("cancel_unpaid_orders: %s ta buyurtma bekor qilindi", cancelled)
