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
        import json as _json

        start = time.monotonic()
        last_user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )

        # Attempt basic keyword matching against materials listed in the
        # system prompt so the stub behaves like the real intent extractor.
        found = []
        lowered = last_user.lower()
        for line in system.splitlines():
            line = line.strip()
            if line.startswith("- ") and line != "- (hozircha materiallar yo'q)":
                mat_name = line[2:].strip()
                if mat_name.lower() in lowered:
                    found.append(mat_name)

        if found:
            msg = f"Sizga {', '.join(found)} materialidagi pardalarni tavsiya qilaman!"
        else:
            msg = (
                "Assalomu alaykum! Men ZigZag AI maslahatchisiman. "
                "Sizga premium pardalar tanlashda qanday yordam bera olaman?"
            )

        content = _json.dumps({"message": msg, "materials": found}, ensure_ascii=False)
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


class OpenAIProvider:
    def __init__(self, model):
        import openai

        self.model = model
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

    def chat(self, system, messages, max_tokens):
        start = time.monotonic()
        api_messages = [{"role": "system", "content": system}] + messages
        response = self.client.chat.completions.create(
            model=self.model,
            messages=api_messages,
            max_tokens=max_tokens,
        )
        latency = int((time.monotonic() - start) * 1000)
        content = response.choices[0].message.content
        return ChatResult(
            content=content,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            model=self.model,
            latency_ms=latency,
        )


def get_chat_provider(strong=False):
    if settings.AI_STUB_MODE:
        return StubProvider()
    
    provider_type = getattr(settings, "AI_PROVIDER", "anthropic").lower()
    model = settings.AI_CHAT_MODEL_STRONG if strong else settings.AI_CHAT_MODEL
    
    if provider_type == "openai":
        if not settings.OPENAI_API_KEY:
            return StubProvider()
        return OpenAIProvider(model)
        
    if not settings.ANTHROPIC_API_KEY:
        return StubProvider()
    return AnthropicProvider(model)
