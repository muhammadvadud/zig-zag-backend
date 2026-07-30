"""System prompt va prompt-injection himoyalari.

Refaktor natijasida prompt sezilarli darajada qisqartirildi:
  - materiallar, ranglar va boshqa metadata prompt ichiga hardcode qilinMAYDI
  - misollar qisqartirildi
  - takrorlangan qoidalar olib tashlandi
  - har bir qoida faqat bir marta yozilgan

Bu fayl endi faqat:
  1. Injection aniqlash
  2. Sanitizatsiya
  3. Legacy SYSTEM_PROMPT (backward compat uchun)
"""

# Legacy prompt — tashqi import uchun saqlanmoqda
SYSTEM_PROMPT = (
    "Siz ZIG ZAG — premium pardalar onlayn do'koni uchun yordamchisiz. "
    "Faqat pardalar, matolar, ranglar, dizayn, o'lcham, xizmat tariflari va "
    "buyurtma bo'yicha yordam berasiz. Boshqa mavzularga javob bermaysiz."
)


# ── Prompt-injection himoyasi ───────────────────────────────────────────────

_INJECTION_MARKERS = (
    "ignore previous",
    "ignore all previous",
    "disregard previous",
    "forget your instructions",
    "system prompt",
    "avvalgi ko'rsatmalarni unut",
    "ko'rsatmalarni e'tiborsiz",
    "reveal your prompt",
)


def looks_like_injection(text):
    """Prompt-injection urinishini aniqlash."""
    lowered = text.lower()
    return any(marker in lowered for marker in _INJECTION_MARKERS)


def sanitize_user_input(text):
    """Foydalanuvchi kiritmasini tozalash — control belgilar olib tashlanadi."""
    return "".join(ch for ch in text if ch == "\n" or ch >= " ").strip()
