"""Telegram bot — xodim/menejer/adminga zakaz bildirishnomalarini yuborish.

Stdlib ``urllib`` bilan yozilgan (loyihaga yangi HTTP kutubxona qo'shmaslik
uchun) — Telegram Bot API oddiy JSON-over-HTTPS bo'lgani uchun bu yetarli.
Token bo'sh bo'lsa hech narsa yubormaydi va xato ko'tarmaydi (dev muhitida
bot sozlanmagan bo'lishi mumkin).
"""

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org"
TIMEOUT = 10


def _api_url(method):
    token = settings.TELEGRAM_BOT_TOKEN
    return f"{API_BASE}/bot{token}/{method}"


def api_call(method, params=None, timeout=TIMEOUT):
    """Telegram Bot API'ga past darajadagi chaqiruv. Token yo'q bo'lsa None."""

    if not settings.TELEGRAM_BOT_TOKEN:
        logger.info("Telegram bot token sozlanmagan — '%s' chaqirilmadi.", method)
        return None

    data = json.dumps(params or {}).encode("utf-8")
    req = urllib.request.Request(
        _api_url(method),
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError:
        logger.exception("Telegram API xatosi: %s", method)
        return None


def send_message(chat_id, text):
    """Berilgan chat_id'ga xabar yuboradi. Token bo'lmasa yoki xato bo'lsa jim
    o'tadi (bildirishnoma oqimi hech qachon shu tufayli buzilmasligi kerak)."""

    if not chat_id:
        return False
    result = api_call(
        "sendMessage",
        {"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
    )
    return bool(result and result.get("ok"))
