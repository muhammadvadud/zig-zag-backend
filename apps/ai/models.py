import uuid

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


def gen_public_id():
    return f"gen_{uuid.uuid4().hex[:16]}"


class AIConversation(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ai_conversations",
    )
    session_key = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    title = models.CharField(max_length=200, blank=True)
    is_archived = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]


class AIMessage(BaseModel):
    ROLE_CHOICES = (("user", "user"), ("assistant", "assistant"), ("system", "system"))

    conversation = models.ForeignKey(
        AIConversation, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.TextField()
    input_tokens = models.PositiveIntegerField(null=True, blank=True)
    output_tokens = models.PositiveIntegerField(null=True, blank=True)
    model = models.CharField(max_length=64, blank=True)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]


class AIImageGeneration(BaseModel):
    STATUS_CHOICES = (
        ("queued", "queued"),
        ("processing", "processing"),
        ("done", "done"),
        ("failed", "failed"),
    )

    public_id = models.CharField(max_length=40, unique=True, default=gen_public_id)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_images")
    source_image = models.ImageField(upload_to="ai/source/", null=True, blank=True)
    product = models.ForeignKey(
        "catalog.Product", on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_images"
    )
    prompt = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="queued")
    result_image = models.ImageField(upload_to="ai/result/", null=True, blank=True)
    cost_tokens = models.PositiveIntegerField(null=True, blank=True)
    cost_credits = models.PositiveIntegerField(default=1)
    idempotency_key = models.CharField(max_length=64, blank=True, db_index=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.public_id


class AIUsageQuota(BaseModel):
    """Per-user monthly counters; limits are copied from the user's tariff."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_quotas")
    period = models.CharField(max_length=7)  # e.g. "2026-06"
    tokens_used = models.PositiveIntegerField(default=0)
    images_used = models.PositiveIntegerField(default=0)
    messages_used = models.PositiveIntegerField(default=0)
    token_limit = models.PositiveIntegerField(default=0)
    image_limit = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("user", "period")
        ordering = ["-period"]
