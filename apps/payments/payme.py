"""Minimal Payme Merchant API (JSON-RPC) handler.

The amount sent by Payme is in tiyin and is always re-validated against the
order total on the server. Transactions are idempotent on the Payme transaction
id, so a webhook replay never double-charges.
"""

import base64

from django.conf import settings
from django.utils import timezone

from apps.orders.models import Order

from .models import Payment

# Payme JSON-RPC error codes.
ERR_AUTH = -32504
ERR_METHOD = -32601
ERR_INSUFFICIENT_PRIVILEGE = -32504
ERR_INVALID_AMOUNT = -31001
ERR_ORDER_NOT_FOUND = -31050
ERR_TXN_NOT_FOUND = -31003
ERR_CANNOT_PERFORM = -31008
ERR_ORDER_STATE = -31052


def _error(code, message, request_id=None):
    return {"error": {"code": code, "message": message}, "id": request_id}


def _ok(result, request_id=None):
    return {"result": result, "id": request_id}


def check_auth(request):
    header = request.headers.get("Authorization", "")
    if not header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(header[6:]).decode()
    except Exception:
        return False
    _, _, key = decoded.partition(":")
    return bool(settings.PAYME_KEY) and key == settings.PAYME_KEY


def _find_order(params):
    account = params.get("account", {})
    order_number = account.get("order_number")
    if not order_number:
        return None
    return Order.objects.filter(order_number=order_number).first()


def _epoch_ms(dt):
    return int(dt.timestamp() * 1000) if dt else 0


def handle(request, body):
    method = body.get("method")
    params = body.get("params", {})
    request_id = body.get("id")

    if not check_auth(request):
        return _error(ERR_AUTH, "Insufficient privileges", request_id)

    handlers = {
        "CheckPerformTransaction": check_perform,
        "CreateTransaction": create_transaction,
        "PerformTransaction": perform_transaction,
        "CancelTransaction": cancel_transaction,
        "CheckTransaction": check_transaction,
    }
    handler = handlers.get(method)
    if not handler:
        return _error(ERR_METHOD, "Method not found", request_id)
    return handler(params, request_id)


def check_perform(params, request_id):
    order = _find_order(params)
    if not order:
        return _error(ERR_ORDER_NOT_FOUND, "Buyurtma topilmadi", request_id)
    if int(order.total * 100) != int(params.get("amount", 0)):
        return _error(ERR_INVALID_AMOUNT, "Summa noto'g'ri", request_id)
    if order.payment_status == "paid":
        return _error(ERR_ORDER_STATE, "Buyurtma allaqachon to'langan", request_id)
    return _ok({"allow": True}, request_id)


def create_transaction(params, request_id):
    txn_id = params.get("id")
    order = _find_order(params)
    if not order:
        return _error(ERR_ORDER_NOT_FOUND, "Buyurtma topilmadi", request_id)
    if int(order.total * 100) != int(params.get("amount", 0)):
        return _error(ERR_INVALID_AMOUNT, "Summa noto'g'ri", request_id)

    payment, created = Payment.objects.get_or_create(
        provider="payme",
        provider_transaction_id=txn_id,
        defaults={
            "order": order,
            "amount": order.total,
            "state": Payment.STATE_CREATED,
            "raw_payload": params,
        },
    )
    if not created and payment.state != Payment.STATE_CREATED:
        return _error(ERR_CANNOT_PERFORM, "Tranzaksiya holati mos emas", request_id)

    return _ok(
        {
            "create_time": _epoch_ms(payment.created_at),
            "transaction": str(payment.id),
            "state": payment.state,
        },
        request_id,
    )


def perform_transaction(params, request_id):
    payment = Payment.objects.filter(
        provider="payme", provider_transaction_id=params.get("id")
    ).first()
    if not payment:
        return _error(ERR_TXN_NOT_FOUND, "Tranzaksiya topilmadi", request_id)

    if payment.state == Payment.STATE_COMPLETED:
        return _ok(
            {
                "transaction": str(payment.id),
                "perform_time": _epoch_ms(payment.paid_at),
                "state": payment.state,
            },
            request_id,
        )

    payment.state = Payment.STATE_COMPLETED
    payment.paid_at = timezone.now()
    payment.save(update_fields=["state", "paid_at", "updated_at"])

    order = payment.order
    order.payment_status = "paid"
    if order.status == "pending":
        order.status = "paid"
    order.save(update_fields=["payment_status", "status", "updated_at"])

    return _ok(
        {
            "transaction": str(payment.id),
            "perform_time": _epoch_ms(payment.paid_at),
            "state": payment.state,
        },
        request_id,
    )


def cancel_transaction(params, request_id):
    payment = Payment.objects.filter(
        provider="payme", provider_transaction_id=params.get("id")
    ).first()
    if not payment:
        return _error(ERR_TXN_NOT_FOUND, "Tranzaksiya topilmadi", request_id)

    if payment.state in (Payment.STATE_CANCELLED, Payment.STATE_CANCELLED_AFTER_COMPLETE):
        return _ok(
            {
                "transaction": str(payment.id),
                "cancel_time": _epoch_ms(payment.cancelled_at),
                "state": payment.state,
            },
            request_id,
        )

    new_state = (
        Payment.STATE_CANCELLED_AFTER_COMPLETE
        if payment.state == Payment.STATE_COMPLETED
        else Payment.STATE_CANCELLED
    )
    payment.state = new_state
    payment.cancelled_at = timezone.now()
    payment.save(update_fields=["state", "cancelled_at", "updated_at"])

    order = payment.order
    order.payment_status = "refunded" if order.payment_status == "paid" else "failed"
    order.save(update_fields=["payment_status", "updated_at"])

    return _ok(
        {
            "transaction": str(payment.id),
            "cancel_time": _epoch_ms(payment.cancelled_at),
            "state": payment.state,
        },
        request_id,
    )


def check_transaction(params, request_id):
    payment = Payment.objects.filter(
        provider="payme", provider_transaction_id=params.get("id")
    ).first()
    if not payment:
        return _error(ERR_TXN_NOT_FOUND, "Tranzaksiya topilmadi", request_id)
    return _ok(
        {
            "create_time": _epoch_ms(payment.created_at),
            "perform_time": _epoch_ms(payment.paid_at),
            "cancel_time": _epoch_ms(payment.cancelled_at),
            "transaction": str(payment.id),
            "state": payment.state,
            "reason": None,
        },
        request_id,
    )
