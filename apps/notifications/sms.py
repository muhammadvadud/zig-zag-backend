"""SMS yuborish — provayder-stub.

Hozircha real provayder ulanmagan: ``SMS_PROVIDER`` bo'sh bo'lsa xabar shunchaki
logga yoziladi (dev/staging uchun yetarli). Real provayder (masalan Eskiz yoki
PlayMobile) tayyor bo'lganda faqat ``_send_via_provider`` ichini to'ldirish
kifoya — chaqiruvchi kod (``send_sms``) o'zgarmaydi.

Matnlar markazlashtirilgan: ``apps/notifications/sms_templates.py``.
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def send_sms(phone, text):
    """SMS yuboradi. Provayder sozlanmagan bo'lsa — konsolga yozadi (crash bermaydi)."""

    if not text:
        return False

    provider = (settings.SMS_PROVIDER or "").strip().lower()
    if not provider:
        logger.info("SMS (console) -> %s: %s", phone, text)
        return True

    try:
        return _send_via_provider(provider, phone, text)
    except Exception:  # noqa: BLE001 — SMS xatosi buyurtma oqimini to'xtatmasligi kerak
        logger.exception("SMS yuborishda xatolik (%s) -> %s", provider, phone)
        return False


def _send_via_provider(provider, phone, text):
    """Real provayder integratsiyasi shu yerga qo'shiladi (hozircha stub).

    Masalan Eskiz.uz uchun: ``settings.SMS_API_KEY`` bilan avtorizatsiya token
    olinadi, so'ng ``https://notify.eskiz.uz/api/message/sms/send`` ga POST
    qilinadi. PlayMobile uchun shunga o'xshash HTTP so'rov. Hozircha faqat
    struktura tayyor — token/provayder sozlanmaguncha logga yozib turadi.
    """

    logger.info("SMS via %s -> %s: %s", provider, phone, text)
    # TODO: real provayder ulanganda shu yerda HTTP so'rov yuboriladi.
    return True
