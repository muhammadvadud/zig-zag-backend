"""Chat orchestration: context window, provider call, persistence, quota."""

from django.conf import settings
from django.db.models import Q

from apps.catalog.models import Product

from .models import AIMessage
from .prompts import SYSTEM_PROMPT, looks_like_injection, sanitize_user_input
from .providers import get_chat_provider
from .quota import ensure_token_budget, record_usage


def _build_context(conversation):
    """Last N messages only — a sliding window to cap input tokens/cost."""

    window = settings.AI_CONTEXT_WINDOW_MESSAGES
    recent = list(
        conversation.messages.filter(role__in=("user", "assistant"))
        .order_by("-created_at")[:window]
    )
    recent.reverse()
    return [{"role": m.role, "content": m.content} for m in recent]


def suggest_products(text, limit=3):
    qs = (
        Product.objects.filter(is_active=True)
        .filter(
            Q(name_uz__icontains=text)
            | Q(name_ru__icontains=text)
            | Q(material__icontains=text)
            | Q(category__slug__icontains=text)
        )[:limit]
    )
    return [{"id": p.id, "name": p.name_uz, "slug": p.slug} for p in qs]


def handle_user_message(conversation, user, raw_content):
    content = sanitize_user_input(raw_content)
    if not content:
        from apps.common.exceptions import BusinessError

        raise BusinessError("Xabar bo'sh bo'lishi mumkin emas.")
    if len(content) > settings.AI_MAX_INPUT_CHARS:
        from apps.common.exceptions import BusinessError

        raise BusinessError(
            f"Xabar juda uzun (maksimum {settings.AI_MAX_INPUT_CHARS} belgi)."
        )

    quota = None
    if user and user.is_authenticated:
        quota = ensure_token_budget(user)

    # Persist the user's message first so it is part of the saved history.
    AIMessage.objects.create(conversation=conversation, role="user", content=content)

    # A flagged injection attempt is answered with a safe refusal, no LLM call.
    if looks_like_injection(content):
        reply = "Kechirasiz, bu so'rovga yordam bera olmayman. Pardalar bo'yicha savol bering."
        assistant = AIMessage.objects.create(
            conversation=conversation, role="assistant", content=reply, model="guard"
        )
        return assistant, [], quota

    messages = _build_context(conversation)
    provider = get_chat_provider()
    result = provider.chat(
        system=SYSTEM_PROMPT,
        messages=messages,
        max_tokens=settings.AI_MAX_OUTPUT_TOKENS,
    )

    assistant = AIMessage.objects.create(
        conversation=conversation,
        role="assistant",
        content=result.content,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        model=result.model,
        latency_ms=result.latency_ms,
    )

    if quota is not None:
        record_usage(
            quota,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            messages=1,
        )

    suggestions = suggest_products(content)
    return assistant, suggestions, quota
