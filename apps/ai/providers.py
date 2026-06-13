"""LLM provider abstraction.

The provider key lives only on the backend (never exposed to the frontend).
When no API key is configured the StubProvider returns a deterministic answer
so the whole stack runs in development and CI without external calls or cost.
"""

import logging
import time
from dataclasses import dataclass

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class ChatResult:
    content: str
    input_tokens: int
    output_tokens: int
    model: str
    latency_ms: int


class StubProvider:
    """Offline fallback used when AI_STUB_MODE is on."""

    model = "stub"

    def chat(self, system, messages, max_tokens):
        start = time.monotonic()
        last_user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )
        content = (
            "Pardalar bo'yicha yordam bera olaman. Siz so'radingiz: "
            f"\"{last_user[:120]}\". Yotoqxona uchun blackout yoki velvet, "
            "mehmonxona uchun linen yoki sheer pardalarni tavsiya qilaman."
        )
        latency = int((time.monotonic() - start) * 1000)
        approx_in = sum(len(m["content"]) for m in messages) // 4
        return ChatResult(
            content=content,
            input_tokens=approx_in,
            output_tokens=len(content) // 4,
            model=self.model,
            latency_ms=latency,
        )


class AnthropicProvider:
    def __init__(self, model):
        import anthropic

        self.model = model
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def chat(self, system, messages, max_tokens):
        start = time.monotonic()
        response = self.client.messages.create(
            model=self.model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
        )
        latency = int((time.monotonic() - start) * 1000)
        content = "".join(block.text for block in response.content if block.type == "text")
        return ChatResult(
            content=content,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=self.model,
            latency_ms=latency,
        )


def get_chat_provider(strong=False):
    if settings.AI_STUB_MODE or not settings.ANTHROPIC_API_KEY:
        return StubProvider()
    model = settings.AI_CHAT_MODEL_STRONG if strong else settings.AI_CHAT_MODEL
    return AnthropicProvider(model)
