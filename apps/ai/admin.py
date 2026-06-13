from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import AIConversation, AIImageGeneration, AIMessage, AIUsageQuota


class AIMessageInline(TabularInline):
    model = AIMessage
    extra = 0
    readonly_fields = ("role", "content", "input_tokens", "output_tokens", "model", "latency_ms")


@admin.register(AIConversation)
class AIConversationAdmin(ModelAdmin):
    list_display = ("id", "user", "title", "is_archived", "created_at")
    list_filter = ("is_archived",)
    search_fields = ("user__phone", "title")
    inlines = [AIMessageInline]


@admin.register(AIMessage)
class AIMessageAdmin(ModelAdmin):
    list_display = ("conversation", "role", "model", "input_tokens", "output_tokens", "created_at")
    list_filter = ("role", "model")


@admin.register(AIImageGeneration)
class AIImageGenerationAdmin(ModelAdmin):
    list_display = ("public_id", "user", "status", "cost_credits", "created_at")
    list_filter = ("status",)
    search_fields = ("public_id", "user__phone")


@admin.register(AIUsageQuota)
class AIUsageQuotaAdmin(ModelAdmin):
    list_display = ("user", "period", "tokens_used", "token_limit", "images_used", "image_limit")
    list_filter = ("period",)
    search_fields = ("user__phone",)
