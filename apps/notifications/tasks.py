"""Og'ir (tashqi tarmoqqa chiquvchi) bildirishnoma ishlari — Celery orqali,
so'rov oqimini bloklamasligi uchun. Har biri o'zicha xato ko'tarmaydi: bitta
telegram/SMS muvaffaqiyatsizligi buyurtma oqimini hech qachon buzmasligi kerak.
"""

import logging

from celery import shared_task

from .sms import send_sms
from .telegram import send_message

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, ignore_result=True)
def send_telegram_task(self, chat_id, text):
    try:
        send_message(chat_id, text)
    except Exception:  # noqa: BLE001
        logger.exception("Telegram xabarini yuborishda xatolik (chat_id=%s)", chat_id)


@shared_task(bind=True, max_retries=2, ignore_result=True)
def send_sms_task(self, phone, text):
    try:
        send_sms(phone, text)
    except Exception:  # noqa: BLE001
        logger.exception("SMS yuborishda xatolik (phone=%s)", phone)
