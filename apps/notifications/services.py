"""Bildirishnoma orkestratsiyasi: buyurtma hodisalarini sayt (Notification),
Telegram va SMS kanallariga tarqatadi.

Bu modul har doim ``apps/orders`` dagi request oqimidan chaqiriladi (buyurtma
yaratilgach / holat o'zgargach) — shu sabab HAR BIR funksiya o'zini xatodan
himoya qiladi: bildirishnoma yuborilmasa ham buyurtma muvaffaqiyatli qolishi
kerak. Og'ir ish (tashqi HTTP — Telegram/SMS) celery task'ga topshiriladi.
"""

import logging

from apps.accounts.models import User

from .models import Notification
from .sms_templates import render as render_sms
from .tasks import send_sms_task, send_telegram_task

logger = logging.getLogger(__name__)

# Admin — dev-only, operatsion ishni ko'rmaydi; faqat employee/manager operatsion
# bildirishnomalarni (yangi buyurtma, holat) oladi.
ORDER_STAFF_ROLES = ("employee", "manager")

ORDER_NEW_TITLE = {"uz": "Yangi buyurtma", "ru": "Новый заказ"}
ORDER_NEW_BODY = {
    "uz": "#{order_number} — {total} so'm ({customer})",
    "ru": "#{order_number} — {total} сум ({customer})",
}

STATUS_TITLE = {
    "uz": {
        "pending": "Buyurtma qabul qilindi",
        "paid": "To'lov qabul qilindi",
        "processing": "Buyurtma jarayonga tushdi",
        "measuring": "O'lchov bosqichi boshlandi",
        "sewing": "Tikuv bosqichi boshlandi",
        "shipped": "Buyurtma jo'natildi",
        "completed": "Buyurtma yakunlandi",
        "cancelled": "Buyurtma bekor qilindi",
        "refunded": "Mablag' qaytarildi",
    },
    "ru": {
        "pending": "Заказ принят",
        "paid": "Оплата получена",
        "processing": "Заказ в обработке",
        "measuring": "Этап замера начат",
        "sewing": "Этап пошива начат",
        "shipped": "Заказ отправлен",
        "completed": "Заказ завершён",
        "cancelled": "Заказ отменён",
        "refunded": "Средства возвращены",
    },
}

STATUS_BODY = {
    "uz": "Buyurtma #{order_number} holati: {title}.",
    "ru": "Статус заказа #{order_number}: {title}.",
}

# new_status -> qaysi SMS shablon yuboriladi (faqat mijoz uchun muhim bosqichlar).
# 'paid' va 'processing' ikkalasi ham "qabul qilindi" ma'nosida (STZda talab
# qilingandek), 'shipped' — alohida "jo'natildi" xabari.
STATUS_SMS_TEMPLATE = {
    "paid": "ORDER_ACCEPTED",
    "processing": "ORDER_ACCEPTED",
    "shipped": "ORDER_SHIPPED",
}


def _lang(user):
    return user.language if user.language in ("uz", "ru") else "uz"


def _staff_recipients():
    return list(User.objects.filter(role__in=ORDER_STAFF_ROLES, is_active=True))


def _notify_staff_telegram(staff, text_by_lang):
    for member in staff:
        if member.telegram_enabled and member.telegram_chat_id:
            text = text_by_lang.get(_lang(member), text_by_lang["uz"])
            try:
                send_telegram_task.delay(member.telegram_chat_id, text)
            except Exception:  # noqa: BLE001 — celery/broker muammosi bildirishnomani sindirmasin
                logger.exception("Telegram task navbatga qo'yilmadi (user=%s)", member.id)


def notify_new_order(order):
    """Yangi buyurtma haqida operatsion xodimlarga (employee/manager) xabar beradi."""

    try:
        staff = _staff_recipients()
        if not staff:
            return

        customer = order.user.full_name or order.user.phone
        notifications = []
        telegram_by_lang = {}
        for member in staff:
            lang = _lang(member)
            title = ORDER_NEW_TITLE[lang]
            body = ORDER_NEW_BODY[lang].format(
                order_number=order.order_number, total=order.total, customer=customer
            )
            notifications.append(
                Notification(
                    recipient=member,
                    kind=Notification.KIND_ORDER_NEW,
                    title=title,
                    body=body,
                    order=order,
                )
            )
            telegram_by_lang[lang] = f"🆕 {title}\n{body}"

        Notification.objects.bulk_create(notifications)
        _notify_staff_telegram(staff, telegram_by_lang)
    except Exception:  # noqa: BLE001 — bildirishnoma xatosi buyurtmani buzmasligi kerak
        logger.exception("notify_new_order xato berdi (order=%s)", getattr(order, "order_number", None))


def notify_status_change(order, old_status, new_status):
    """Buyurtma holati o'zgarganda: mijozga sayt (+SMS muhim bosqichlarda),
    xodimlarga sayt + telegram orqali xabar beradi."""

    try:
        customer = order.user
        lang = _lang(customer)
        title = STATUS_TITLE.get(lang, STATUS_TITLE["uz"]).get(new_status, new_status)
        body = STATUS_BODY.get(lang, STATUS_BODY["uz"]).format(
            order_number=order.order_number, title=title
        )
        Notification.objects.create(
            recipient=customer,
            kind=Notification.KIND_ORDER_STATUS,
            title=title,
            body=body,
            order=order,
        )

        sms_template = STATUS_SMS_TEMPLATE.get(new_status)
        if sms_template:
            text = render_sms(sms_template, lang, order_number=order.order_number)
            if text:
                try:
                    send_sms_task.delay(customer.phone, text)
                except Exception:  # noqa: BLE001
                    logger.exception("SMS task navbatga qo'yilmadi (order=%s)", order.order_number)

        # Xodimlarga ham (sayt + telegram) — kuzatib borish uchun.
        staff = _staff_recipients()
        if staff:
            staff_notifications = []
            telegram_by_lang = {}
            for member in staff:
                member_lang = _lang(member)
                member_title = STATUS_TITLE.get(member_lang, STATUS_TITLE["uz"]).get(new_status, new_status)
                member_body = STATUS_BODY.get(member_lang, STATUS_BODY["uz"]).format(
                    order_number=order.order_number, title=member_title
                )
                staff_notifications.append(
                    Notification(
                        recipient=member,
                        kind=Notification.KIND_ORDER_STATUS,
                        title=member_title,
                        body=member_body,
                        order=order,
                    )
                )
                telegram_by_lang[member_lang] = f"🔄 {member_title}\n{member_body}"
            Notification.objects.bulk_create(staff_notifications)
            _notify_staff_telegram(staff, telegram_by_lang)
    except Exception:  # noqa: BLE001
        logger.exception(
            "notify_status_change xato berdi (order=%s, %s -> %s)",
            getattr(order, "order_number", None),
            old_status,
            new_status,
        )
