"""Intent Detector — foydalanuvchi maqsadini aniqlash.

Birinchi bosqich: foydalanuvchi xabaridan intent ajratiladi.
LLM faqat intent turini qaytaradi, boshqa hech narsa qilmaydi.

Intentlar:
  - product_search:        mahsulot qidirish / parda tanlash
  - information_question:  pardalar haqida umumiy savol (material, yuvish, dizayn)
  - greeting:              salomlashish
  - unrelated:             pardalar bilan bog'liq bo'lmagan savol
"""

import json
import logging

logger = logging.getLogger(__name__)

INTENT_SYSTEM_PROMPT = (
    "Sen foydalanuvchi maqsadini aniqlaydigan klassifikator.\n"
    "Faqat bitta so'z qaytarasan — intent nomi.\n\n"
    "Intentlar:\n"
    "- product_search — foydalanuvchi parda/mahsulot qidirmoqchi, sotib olmoqchi, "
    "ko'rmoqchi, yoki aniq material/rang/xona/uslub aytmoqda\n"
    "- information_question — pardalar, matolar, yuvish, dizayn haqida umumiy savol\n"
    "- greeting — salomlashish, tanishish\n"
    "- unrelated — pardalar bilan bog'liq bo'lmagan mavzu\n\n"
    "Javob: faqat intent nomini yoz, boshqa hech narsa yozma.\n"
    "Misol: product_search"
)

VALID_INTENTS = {"product_search", "information_question", "greeting", "unrelated"}


def detect_intent(provider, user_message, max_tokens=20):
    """Foydalanuvchi xabaridan intent aniqlash.

    Args:
        provider: LLM provider instance (.chat() metodi bilan).
        user_message: foydalanuvchining so'nggi xabari.
        max_tokens: LLM chiqishi uchun maksimal tokenlar (intent qisqa).

    Returns:
        tuple: (intent_str, ChatResult) — intent nomi va LLM natijasi.
    """
    messages = [{"role": "user", "content": user_message}]

    result = provider.chat(
        system=INTENT_SYSTEM_PROMPT,
        messages=messages,
        max_tokens=max_tokens,
    )

    raw = (result.content or "").strip().lower().replace('"', "").replace("'", "")

    # Intentni validatsiya qilish
    if raw in VALID_INTENTS:
        intent = raw
    else:
        # Agar LLM ortiqcha matn qaytarsa, ichidan intent qidiramiz
        intent = "information_question"  # default fallback
        for valid in VALID_INTENTS:
            if valid in raw:
                intent = valid
                break

    logger.debug("Intent detected: %s (raw: %s)", intent, raw[:50])
    return intent, result
