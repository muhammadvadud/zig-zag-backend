"""Chat orchestration: context window, provider call, persistence, quota."""

import json
import logging

from django.conf import settings
from django.db.models import Q

from apps.catalog.models import Product

from .models import AIMessage
from .prompts import get_dynamic_system_prompt, looks_like_injection, sanitize_user_input
from .providers import get_chat_provider
from .quota import ensure_token_budget, record_usage

logger = logging.getLogger(__name__)


def _build_context(conversation):
    """Last N messages only — a sliding window to cap input tokens/cost."""

    window = settings.AI_CONTEXT_WINDOW_MESSAGES
    recent = list(
        conversation.messages.filter(role__in=("user", "assistant"))
        .order_by("-created_at")[:window]
    )
    recent.reverse()
    return [{"role": m.role, "content": m.content} for m in recent]


# ---------------------------------------------------------------------------
# Intent parsing
# ---------------------------------------------------------------------------

def _parse_intent(raw_content):
    """Parse the LLM's JSON response into a structured intent dict.

    The LLM is instructed to return valid JSON with the shape:
        {"message": "...", "materials": ["Blackout", "Baxmal"]}

    This function is deliberately lenient: if the LLM wraps the JSON in
    markdown fences or adds stray text, we still attempt extraction.

    Returns a dict with at least {"message": "", "materials": []}.
    Designed for easy extension — future filters (colors, styles, rooms,
    price_range, etc.) will be added here with the same pattern.
    """
    default = {"message": "", "materials": []}

    text = raw_content.strip()

    # Strip markdown code fences if present.
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove opening ``` (possibly ```json) and closing ```
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Last resort: try to find a JSON object in the text.
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                logger.warning("Failed to parse LLM intent JSON: %s", text[:200])
                return default
        else:
            logger.warning("No JSON object found in LLM response: %s", text[:200])
            return default

    if not isinstance(data, dict):
        return default

    # Extract the conversational message.
    message = data.get("message", "")
    if not isinstance(message, str):
        message = ""

    # Normalise materials — must be a list of strings.
    materials = data.get("materials", [])
    if not isinstance(materials, list):
        materials = []
    materials = [m for m in materials if isinstance(m, str) and m.strip()]

    return {"message": message, "materials": materials}


# ---------------------------------------------------------------------------
# Product search by extracted filters
# ---------------------------------------------------------------------------

def _search_products_by_filters(filters, limit=6):
    """Query the product catalog using the structured filters.

    Currently supports filtering by material names.
    Designed for easy extension — each new filter type adds an additional
    Q expression with the same pattern.

    Returns a list of dicts with id, title, slug, and main image URL.
    """
    materials = filters.get("materials", [])

    if not materials:
        return []

    qs = Product.objects.filter(is_active=True, is_deleted=False)

    # Build material filter: match any of the extracted material names.
    material_q = Q()
    for mat_name in materials:
        material_q |= Q(materials__name_uz__iexact=mat_name)
        material_q |= Q(materials__name_ru__iexact=mat_name)

    qs = qs.filter(material_q).prefetch_related("images").distinct()[:limit]

    results = []
    for p in qs:
        # Get main image or first available image.
        main_img = p.images.filter(is_main=True).first()
        if not main_img:
            main_img = p.images.first()
        image_url = main_img.image.url if main_img and main_img.image else None

        results.append({
            "id": p.id,
            "title": p.name_uz,
            "slug": p.slug,
            "image": image_url,
        })
    return results


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

    # ---- Step 1: Intent Extraction via LLM ----
    messages = _build_context(conversation)
    provider = get_chat_provider()
    result = provider.chat(
        system=get_dynamic_system_prompt(),
        messages=messages,
        max_tokens=settings.AI_MAX_OUTPUT_TOKENS,
    )

    # Parse the structured JSON from the LLM response.
    intent = _parse_intent(result.content)

    # Use the conversational message for the user; fall back to raw content.
    reply_text = intent["message"] or result.content

    # Persist the conversational message as the assistant reply.
    assistant = AIMessage.objects.create(
        conversation=conversation,
        role="assistant",
        content=reply_text,
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

    # ---- Step 2: Backend SQL Search ----
    suggestions = _search_products_by_filters(intent)

    # ---- Debug: Token Usage Logging ----
    if getattr(settings, "AI_DEBUG_TOKENS", False):
        total_tokens = (result.input_tokens or 0) + (result.output_tokens or 0)
        user_id = user.id if user and user.is_authenticated else "anonymous"
        user_phone = getattr(user, "phone", "—") if user and user.is_authenticated else "—"
        logger.info(
            "\n"
            "╔══════════════════════════════════════════════════════════════╗\n"
            "║                   AI TOKEN DEBUG LOG                       ║\n"
            "╠══════════════════════════════════════════════════════════════╣\n"
            "║  User ID       : %-40s  ║\n"
            "║  User Phone    : %-40s  ║\n"
            "║  Conversation  : %-40s  ║\n"
            "║  Message ID    : %-40s  ║\n"
            "║  Model         : %-40s  ║\n"
            "║  Input Tokens  : %-40s  ║\n"
            "║  Output Tokens : %-40s  ║\n"
            "║  Total Tokens  : %-40s  ║\n"
            "║  Latency       : %-40s  ║\n"
            "║  Materials     : %-40s  ║\n"
            "║  Products Found: %-40s  ║\n"
            "╚══════════════════════════════════════════════════════════════╝",
            user_id,
            user_phone,
            conversation.id,
            assistant.id,
            result.model,
            result.input_tokens,
            result.output_tokens,
            total_tokens,
            f"{result.latency_ms} ms",
            ", ".join(intent["materials"]) or "—",
            len(suggestions),
        )

    return assistant, suggestions, quota

