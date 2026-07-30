"""Filter Extractor — mahsulot qidirish filtrlari ajratish.

Ikkinchi bosqich: agar intent = product_search bo'lsa,
foydalanuvchi xabaridan filtrlarni strukturalangan JSON sifatida ajratadi.

Bu yerda:
  - foydalanuvchiga javob yozilMAYDI
  - marketing matni yozilMAYDI
  - faqat JSON qaytariladi
  - filter qiymatlari foydalanuvchi tilida qaytariladi (ichki sluglar emas)
"""

import json
import logging

logger = logging.getLogger(__name__)


def _build_filter_prompt(metadata):
    """Metadata asosida filter extraction prompt yaratish.

    Metadata backend tomonidan runtime da yuboriladi,
    prompt ichiga hardcode qilinmaydi.

    Args:
        metadata: dict — {materials: [...], colors: [...], rooms: [...],
                          styles: [...], categories: [...]}
    """
    sections = []
    for key, label in [
        ("materials", "Materiallar"),
        ("colors", "Ranglar"),
        ("rooms", "Xonalar"),
        ("styles", "Uslublar"),
        ("categories", "Kategoriyalar"),
    ]:
        items = metadata.get(key, [])
        if items:
            items_str = ", ".join(items)
            sections.append(f"{label}: {items_str}")

    metadata_block = "\n".join(sections) if sections else "(metadata yo'q)"

    return (
        "Sen foydalanuvchi xabaridan parda qidirish filtrlarini ajratasan.\n"
        "Faqat JSON qaytar. Boshqa hech narsa yozma.\n"
        "Javob yozma. Salomlashma. Maslahat berma.\n\n"
        "Qiymatlarni foydalanuvchi ishlatgan tilda qaytar.\n"
        "Masalan foydalanuvchi 'oshxona' desa → room: 'oshxona',\n"
        "'кухня' desa → room: 'кухня'.\n\n"
        f"Mavjud qiymatlar:\n{metadata_block}\n\n"
        "JSON formati:\n"
        "{\n"
        '  "intent": "product_search",\n'
        '  "filters": {\n'
        '    "materials": [],\n'
        '    "colors": [],\n'
        '    "room": null,\n'
        '    "style": null,\n'
        '    "pattern": null,\n'
        '    "category": null,\n'
        '    "width": null,\n'
        '    "height": null\n'
        "  },\n"
        '  "missing": []\n'
        "}\n\n"
        "Qoidalar:\n"
        "- Faqat foydalanuvchi aytgan filtrlarni to'ldir\n"
        "- Aytilmagan filtrlar null yoki bo'sh qolsin\n"
        "- missing ga yetishmayotgan muhim ma'lumotlarni yoz "
        "(masalan: width, height)\n"
        "- message yoki tabiiy matn qo'shma\n"
    )


def _parse_filter_json(raw_content):
    """LLM javobidan JSON ajratib olish.

    LLM ba'zan markdown fence ichiga o'rab yuboradi —
    buni tozalash kerak.

    Returns:
        dict yoki None agar parse qilolmasa.
    """
    if not raw_content:
        return None

    text = str(raw_content).strip()

    # Markdown code fences olib tashlash
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # JSON topishga harakat
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                logger.warning("Filter JSON parse xatosi: %s", text[:200])
                return None

    return None


def _normalize_filters(data):
    """Parse qilingan JSON ni standart filter formatiga keltirish."""
    default = {
        "intent": "product_search",
        "filters": {
            "materials": [],
            "colors": [],
            "room": None,
            "style": None,
            "pattern": None,
            "category": None,
            "width": None,
            "height": None,
        },
        "missing": [],
    }

    if not isinstance(data, dict):
        return default

    filters = data.get("filters", {})
    if not isinstance(filters, dict):
        filters = {}

    # materials va colors — list bo'lishi kerak
    materials = filters.get("materials", [])
    if not isinstance(materials, list):
        materials = [materials] if materials else []
    materials = [m for m in materials if isinstance(m, str) and m.strip()]

    colors = filters.get("colors", [])
    if not isinstance(colors, list):
        colors = [colors] if colors else []
    colors = [c for c in colors if isinstance(c, str) and c.strip()]

    # Skalar qiymatlar
    def _str_or_none(val):
        if isinstance(val, str) and val.strip():
            return val.strip()
        return None

    # width/height — raqam yoki None
    def _num_or_none(val):
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    # missing — list bo'lishi kerak
    missing = data.get("missing", [])
    if not isinstance(missing, list):
        missing = []
    missing = [m for m in missing if isinstance(m, str)]

    return {
        "intent": "product_search",
        "filters": {
            "materials": materials,
            "colors": colors,
            "room": _str_or_none(filters.get("room")),
            "style": _str_or_none(filters.get("style")),
            "pattern": _str_or_none(filters.get("pattern")),
            "category": _str_or_none(filters.get("category")),
            "width": _num_or_none(filters.get("width")),
            "height": _num_or_none(filters.get("height")),
        },
        "missing": missing,
    }


def extract_filters(provider, user_message, metadata, max_tokens=300):
    """Foydalanuvchi xabaridan filtrlarni ajratish.

    Args:
        provider: LLM provider instance.
        user_message: foydalanuvchining so'nggi xabari.
        metadata: dict — mavjud materiallar, ranglar, etc. (runtime dan).
        max_tokens: LLM chiqishi uchun maksimal tokenlar.

    Returns:
        tuple: (filters_dict, ChatResult) — strukturalangan filtrlar va LLM natijasi.
    """
    system_prompt = _build_filter_prompt(metadata)
    messages = [{"role": "user", "content": user_message}]

    result = provider.chat(
        system=system_prompt,
        messages=messages,
        max_tokens=max_tokens,
    )

    parsed = _parse_filter_json(result.content)
    filters = _normalize_filters(parsed)

    logger.debug("Extracted filters: %s", filters)
    return filters, result
