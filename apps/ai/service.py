"""Chat orchestration: intent → filter → search → response.

Yangi arxitektura:
  1. Intent Detection   — foydalanuvchi maqsadini aniqlash
  2. Filter Extraction  — product_search uchun filtrlarni ajratish
  3. Product Search     — bazadan mahsulot qidirish
  4. Response Generation — foydalanuvchiga javob yozish

Har bir bosqich alohida modul tomonidan bajariladi.
History ga faqat tabiiy suhbat yoziladi (ichki JSON emas).
"""

import logging

from django.conf import settings

from .models import AIMessage
from .prompts import looks_like_injection, sanitize_user_input
from .providers import get_chat_provider
from .quota import ensure_token_budget, record_usage
from .services import (
    build_metadata,
    detect_intent,
    extract_filters,
    generate_response,
    search_products,
)

logger = logging.getLogger(__name__)


def _build_context(conversation):
    """So'nggi N ta tabiiy suhbat xabarlarini olish (sliding window).

    Ichki JSON natijalar (filter extraction) historyga yozilmaydi,
    shuning uchun bu yerda faqat user/assistant role li xabarlar qaytariladi.
    """
    window = settings.AI_CONTEXT_WINDOW_MESSAGES
    recent = list(
        conversation.messages.filter(role__in=("user", "assistant"))
        .order_by("-created_at")[:window]
    )
    recent.reverse()
    return [{"role": m.role, "content": m.content} for m in recent]


def handle_user_message(conversation, user, raw_content):
    """Foydalanuvchi xabarini qayta ishlash — asosiy orkestratsiya.

    Args:
        conversation: AIConversation instance.
        user: User instance (yoki None).
        raw_content: foydalanuvchining xom xabari.

    Returns:
        tuple: (assistant_message, suggestions, quota)
    """
    content = sanitize_user_input(raw_content)
    if not content:
        from apps.common.exceptions import BusinessError
        raise BusinessError("Xabar bo'sh bo'lishi mumkin emas.")

    if len(content) > settings.AI_MAX_INPUT_CHARS:
        from apps.common.exceptions import BusinessError
        raise BusinessError(
            f"Xabar juda uzun (maksimum {settings.AI_MAX_INPUT_CHARS} belgi)."
        )

    # Kvota tekshiruvi
    quota = None
    if user and user.is_authenticated:
        quota = ensure_token_budget(user)

    # Foydalanuvchi xabarini saqlash
    AIMessage.objects.create(conversation=conversation, role="user", content=content)

    # Injection tekshiruvi — LLM chaqirilmaydi
    if looks_like_injection(content):
        reply = "Kechirasiz, bu so'rovga yordam bera olmayman. Pardalar bo'yicha savol bering."
        assistant = AIMessage.objects.create(
            conversation=conversation, role="assistant", content=reply, model="guard"
        )
        return assistant, [], quota

    # Provider olish
    provider = get_chat_provider()

    # Token sarfini kuzatish uchun yig'uvchi
    total_input_tokens = 0
    total_output_tokens = 0

    # ──────────────────────────────────────────────────────────────────────
    # 1-BOSQICH: Intent Detection
    # ──────────────────────────────────────────────────────────────────────
    intent, intent_result = detect_intent(provider, content)
    total_input_tokens += intent_result.input_tokens or 0
    total_output_tokens += intent_result.output_tokens or 0

    suggestions = []
    filters_data = None

    # ──────────────────────────────────────────────────────────────────────
    # 2-BOSQICH: Filter Extraction (faqat product_search uchun)
    # ──────────────────────────────────────────────────────────────────────
    if intent == "product_search":
        metadata = build_metadata()
        filters_data, filter_result = extract_filters(
            provider, content, metadata,
            max_tokens=settings.AI_MAX_OUTPUT_TOKENS,
        )
        total_input_tokens += filter_result.input_tokens or 0
        total_output_tokens += filter_result.output_tokens or 0

        # ──────────────────────────────────────────────────────────────────
        # 3-BOSQICH: Product Search (bazadan qidirish)
        # ──────────────────────────────────────────────────────────────────
        suggestions = search_products(filters_data)

    # ──────────────────────────────────────────────────────────────────────
    # 4-BOSQICH: Response Generation
    # ──────────────────────────────────────────────────────────────────────
    conversation_messages = _build_context(conversation)

    missing = filters_data.get("missing", []) if filters_data else None
    filters_for_response = filters_data.get("filters") if filters_data else None

    reply_text, response_result = generate_response(
        provider=provider,
        conversation_messages=conversation_messages,
        intent=intent,
        max_tokens=settings.AI_MAX_OUTPUT_TOKENS,
        filters=filters_for_response,
        suggestions=suggestions,
        missing=missing,
    )
    total_input_tokens += response_result.input_tokens or 0
    total_output_tokens += response_result.output_tokens or 0

    # ──────────────────────────────────────────────────────────────────────
    # Natijani saqlash — faqat tabiiy javob historyga yoziladi
    # ──────────────────────────────────────────────────────────────────────
    assistant = AIMessage.objects.create(
        conversation=conversation,
        role="assistant",
        content=reply_text,
        input_tokens=total_input_tokens,
        output_tokens=total_output_tokens,
        model=response_result.model,
        latency_ms=response_result.latency_ms,
        suggested_products=suggestions if suggestions else None,
    )

    if quota is not None:
        record_usage(
            quota,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            messages=1,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Debug logging
    # ──────────────────────────────────────────────────────────────────────
    if getattr(settings, "AI_DEBUG_TOKENS", False):
        total_tokens = total_input_tokens + total_output_tokens
        user_id = user.id if user and user.is_authenticated else "anonymous"
        user_phone = getattr(user, "phone", "—") if user and user.is_authenticated else "—"

        materials_str = "None"
        if filters_data and filters_data.get("filters", {}).get("materials"):
            materials_str = ", ".join(filters_data["filters"]["materials"])

        logger.info(
            "AI_TOKEN_DEBUG | User: %s (%s) | Conv: %s | Msg: %s | "
            "Model: %s | Intent: %s | Tokens: %s IN + %s OUT = %s TOT | "
            "Latency: %s | Materials: %s | Found: %s\n",
            user_id,
            user_phone,
            conversation.id,
            assistant.id,
            response_result.model,
            intent,
            total_input_tokens,
            total_output_tokens,
            total_tokens,
            f"{response_result.latency_ms}ms",
            materials_str,
            len(suggestions),
        )

    return assistant, suggestions, quota
