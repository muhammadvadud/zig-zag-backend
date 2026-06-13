import base64

from django.conf import settings

from apps.common.utils import get_client_ip


def build_payment_url(order, provider):
    """Return the hosted checkout URL the frontend should redirect to.

    Amounts are sent in tiyin (1 so'm = 100 tiyin) as both providers expect.
    """

    amount_tiyin = int(order.total * 100)
    if provider == "payme":
        merchant = settings.PAYME_MERCHANT_ID
        raw = f"m={merchant};ac.order_number={order.order_number};a={amount_tiyin}"
        token = base64.b64encode(raw.encode()).decode()
        return f"https://checkout.paycom.uz/{token}"
    if provider == "click":
        return (
            "https://my.click.uz/services/pay"
            f"?service_id={settings.CLICK_SERVICE_ID}"
            f"&merchant_id={settings.CLICK_MERCHANT_ID}"
            f"&amount={order.total}"
            f"&transaction_param={order.order_number}"
        )
    return ""


def ip_allowed(request, allowlist):
    """Return True when the caller IP is permitted (empty list = allow all)."""

    if not allowlist:
        return True
    return get_client_ip(request) in allowlist
