"""Click Prepare/Complete webhook handler.

The md5 signature is mandatory and the amount is re-validated server-side.
Completion is idempotent on the Click transaction id.
"""

import hashlib

from django.conf import settings
from django.utils import timezone

from apps.orders.models import Order

from .models import Payment

ACTION_PREPARE = "0"
ACTION_COMPLETE = "1"

# Click error codes.
ERR_SUCCESS = 0
ERR_SIGN = -1
ERR_AMOUNT = -2
ERR_ACTION = -3
ERR_ALREADY_PAID = -4
ERR_ORDER_NOT_FOUND = -5
ERR_TXN_CANCELLED = -9


def _md5(value):
    return hashlib.md5(value.encode()).hexdigest()


def _check_sign(data, is_complete):
    parts = [
        data.get("click_trans_id", ""),
        data.get("service_id", ""),
        settings.CLICK_SECRET_KEY,
        data.get("merchant_trans_id", ""),
    ]
    if is_complete:
        parts.append(data.get("merchant_prepare_id", ""))
    parts += [
        data.get("amount", ""),
        data.get("action", ""),
        data.get("sign_time", ""),
    ]
    expected = _md5("".join(str(p) for p in parts))
    return expected == data.get("sign_string", "")


def _response(data, error, note, merchant_prepare_id=None):
    payload = {
        "click_trans_id": data.get("click_trans_id"),
        "merchant_trans_id": data.get("merchant_trans_id"),
        "error": error,
        "error_note": note,
    }
    if merchant_prepare_id is not None:
        payload["merchant_prepare_id"] = merchant_prepare_id
    return payload


def handle(data):
    action = str(data.get("action"))
    is_complete = action == ACTION_COMPLETE

    if not _check_sign(data, is_complete):
        return _response(data, ERR_SIGN, "Imzo tekshiruvi muvaffaqiyatsiz")

    order = Order.objects.filter(order_number=data.get("merchant_trans_id")).first()
    if not order:
        return _response(data, ERR_ORDER_NOT_FOUND, "Buyurtma topilmadi")

    try:
        amount = float(data.get("amount", 0))
    except (TypeError, ValueError):
        return _response(data, ERR_AMOUNT, "Summa noto'g'ri")
    if abs(amount - float(order.total)) > 0.01:
        return _response(data, ERR_AMOUNT, "Summa mos emas")

    if action == ACTION_PREPARE:
        return _prepare(data, order)
    if action == ACTION_COMPLETE:
        return _complete(data, order)
    return _response(data, ERR_ACTION, "Noma'lum amal")


def _prepare(data, order):
    if order.payment_status == "paid":
        return _response(data, ERR_ALREADY_PAID, "Allaqachon to'langan")

    payment, _ = Payment.objects.get_or_create(
        provider="click",
        provider_transaction_id=data.get("click_trans_id"),
        defaults={
            "order": order,
            "amount": order.total,
            "state": Payment.STATE_CREATED,
            "raw_payload": data,
        },
    )
    return _response(data, ERR_SUCCESS, "Success", merchant_prepare_id=str(payment.id))


def _complete(data, order):
    payment = Payment.objects.filter(
        provider="click", provider_transaction_id=data.get("click_trans_id")
    ).first()
    if not payment:
        return _response(data, ERR_ORDER_NOT_FOUND, "Tranzaksiya topilmadi")

    if payment.state == Payment.STATE_COMPLETED:
        return _response(data, ERR_SUCCESS, "Success", merchant_prepare_id=str(payment.id))

    payment.state = Payment.STATE_COMPLETED
    payment.paid_at = timezone.now()
    payment.save(update_fields=["state", "paid_at", "updated_at"])

    order.payment_status = "paid"
    if order.status == "pending":
        order.status = "paid"
    order.save(update_fields=["payment_status", "status", "updated_at"])

    return _response(data, ERR_SUCCESS, "Success", merchant_prepare_id=str(payment.id))
