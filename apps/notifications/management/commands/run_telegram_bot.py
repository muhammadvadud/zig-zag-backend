"""Telegram botni long-polling rejimida ishga tushiradi.

Xodim/menejer/admin ``/start`` yozganda kontakt (telefon raqami) so'raladi;
ulashilgan raqam ``accounts.User`` dagi xodim (role in employee/manager/admin)
bilan mos kelsa — ``telegram_chat_id`` saqlanadi va ``telegram_enabled=True``
qilinadi, shundan keyin u buyurtma bildirishnomalarini shu bot orqali oladi.
Nostaff (mijoz) raqamlariga muloyim rad javobi beriladi.

Ishga tushirish: ``python manage.py run_telegram_bot``
Token (``TELEGRAM_BOT_TOKEN``) sozlanmagan bo'lsa — ogohlantirib, darhol chiqadi
(hech qanday xato bermaydi, prod bo'lmagan muhitda xavfsiz)."""

import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.notifications.telegram import api_call

logger = logging.getLogger(__name__)

STAFF_ROLES = ("employee", "manager", "admin")

CONTACT_KEYBOARD = {
    "keyboard": [[{"text": "\U0001F4F1 Raqamni ulashish", "request_contact": True}]],
    "resize_keyboard": True,
    "one_time_keyboard": True,
}


def _normalize_phone(raw):
    """Telegram kontaktidan kelgan raqamni loyihadagi +998XXXXXXXXX formatiga keltiradi."""

    raw = (raw or "").strip().replace(" ", "").replace("-", "")
    if not raw:
        return ""
    if not raw.startswith("+"):
        raw = "+" + raw
    return raw


def _send(chat_id, text, reply_markup=None):
    params = {"chat_id": chat_id, "text": text}
    if reply_markup:
        params["reply_markup"] = reply_markup
    api_call("sendMessage", params)


class Command(BaseCommand):
    help = "Telegram bildirishnoma botini long-polling rejimida ishga tushiradi."

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            self.stdout.write(
                self.style.WARNING("TELEGRAM_BOT_TOKEN sozlanmagan — bot ishga tushmaydi.")
            )
            return

        self.stdout.write(self.style.SUCCESS("Telegram bot ishga tushdi (long polling)..."))
        offset = None
        while True:
            params = {"timeout": 25}
            if offset is not None:
                params["offset"] = offset
            result = api_call("getUpdates", params, timeout=30)
            if not result or not result.get("ok"):
                time.sleep(3)
                continue
            for update in result.get("result", []):
                offset = update["update_id"] + 1
                try:
                    self._handle_update(update)
                except Exception:  # noqa: BLE001 — bitta update xatosi botni to'xtatmasin
                    logger.exception("Telegram update ishlov berishda xato: %s", update)

    def _handle_update(self, update):
        message = update.get("message")
        if not message:
            return
        chat_id = message["chat"]["id"]
        text = (message.get("text") or "").strip()
        contact = message.get("contact")

        if contact:
            self._handle_contact(chat_id, contact)
            return

        if text.startswith("/start"):
            _send(
                chat_id,
                "Assalomu alaykum! ZIG ZAG bildirishnoma botiga xush kelibsiz.\n"
                "Xodim yoki menejer sifatida buyurtma bildirishnomalarini olish uchun "
                "pastdagi tugma orqali telefon raqamingizni ulashing.",
                reply_markup=CONTACT_KEYBOARD,
            )
            return

        _send(chat_id, "Telefon raqamingizni ulashish uchun /start buyrug'ini yuboring.")

    def _handle_contact(self, chat_id, contact):
        phone = _normalize_phone(contact.get("phone_number"))
        user = User.objects.filter(phone=phone, role__in=STAFF_ROLES, is_active=True).first()
        if not user:
            _send(
                chat_id,
                "Kechirasiz, bu raqam xodimlar ro'yxatida topilmadi. "
                "Agar bu xato bo'lsa, administratorga murojaat qiling.",
            )
            return
        user.telegram_chat_id = str(chat_id)
        user.telegram_enabled = True
        user.save(update_fields=["telegram_chat_id", "telegram_enabled"])
        _send(
            chat_id,
            f"Rahmat, {user.full_name or user.phone}! "
            "Endi buyurtma bildirishnomalarini shu yerdan olasiz.",
        )
