"""ZIG ZAG — barcha SMS matnlari BIR joyda.

Bu fayl SMS provayder (Eskiz / PlayMobile) ga tasdiqlash uchun yuboriladigan
"eslon" matn ro'yxati sifatida ham ishlatiladi — shuning uchun matnlar aniq,
o'zgaruvchilar ``{...}`` bilan belgilangan va sharhlar bilan tushuntirilgan.

Har bir shablon uz/ru juftlikda beriladi. Ishlatish:

    from apps.notifications.sms_templates import render
    text = render("ORDER_ACCEPTED", "uz", order_number="ZZ-2026-000123")

Yangi SMS matni kerak bo'lsa — shu faylga qo'shing, boshqa joyda SMS matni
yozilmasin (xizmat provayderiga yuboriladigan ro'yxat shu yerdan olinadi).
"""

BRAND = "ZIG ZAG"

# --------------------------------------------------------------------------- #
# OTP (kirish/ro'yxatdan o'tish tasdiqlash kodi)
# --------------------------------------------------------------------------- #
OTP_CODE = {
    "uz": f"{BRAND} tasdiqlash kodi: {{code}}. Kodni hech kimga aytmang.",
    "ru": f"Код подтверждения {BRAND}: {{code}}. Никому не сообщайте код.",
}

# --------------------------------------------------------------------------- #
# Buyurtma holati — mijozga yuboriladigan SMS'lar
# --------------------------------------------------------------------------- #

# Buyurtma qabul qilindi / to'lov tasdiqlandi va ishlab chiqarishga tushdi.
ORDER_ACCEPTED = {
    "uz": f"{BRAND}: buyurtmangiz #{{order_number}} qabul qilindi va tayyorlanmoqda. Rahmat!",
    "ru": f"{BRAND}: ваш заказ #{{order_number}} принят и готовится. Спасибо!",
}

# Buyurtma jo'natildi / yetkazishga chiqdi.
ORDER_SHIPPED = {
    "uz": f"{BRAND}: buyurtmangiz #{{order_number}} jo'natildi va tez orada yetkaziladi.",
    "ru": f"{BRAND}: ваш заказ #{{order_number}} отправлен и скоро будет доставлен.",
}

# Buyurtma yakunlandi (yetkazib berildi).
ORDER_COMPLETED = {
    "uz": f"{BRAND}: buyurtmangiz #{{order_number}} yetkazildi. Xaridingiz uchun rahmat!",
    "ru": f"{BRAND}: ваш заказ #{{order_number}} доставлен. Спасибо за покупку!",
}

# Buyurtma bekor qilindi.
ORDER_CANCELLED = {
    "uz": f"{BRAND}: buyurtmangiz #{{order_number}} bekor qilindi.",
    "ru": f"{BRAND}: ваш заказ #{{order_number}} отменён.",
}

TEMPLATES = {
    "OTP_CODE": OTP_CODE,
    "ORDER_ACCEPTED": ORDER_ACCEPTED,
    "ORDER_SHIPPED": ORDER_SHIPPED,
    "ORDER_COMPLETED": ORDER_COMPLETED,
    "ORDER_CANCELLED": ORDER_CANCELLED,
}


def render(name, lang, **kwargs):
    """Shablonni tanlangan tilda (uz/ru, aks holda uz) matn qilib qaytaradi."""

    template = TEMPLATES.get(name, {})
    text = template.get(lang) or template.get("uz") or ""
    return text.format(**kwargs) if text else ""
