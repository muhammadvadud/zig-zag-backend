from django.contrib import admin

from .models import AIConversation, AIImageGeneration, AIMessage, AIUsageQuota


class AIMessageInline(admin.TabularInline):
    model = AIMessage
    extra = 0
    readonly_fields = ("role", "content", "input_tokens", "output_tokens", "model", "latency_ms")


@admin.register(AIConversation)
class AIConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "is_archived", "created_at")
    list_filter = ("is_archived",)
    inlines = [AIMessageInline]


@admin.register(AIImageGeneration)
class AIImageGenerationAdmin(admin.ModelAdmin):
    list_display = ("public_id", "user", "status", "cost_credits", "created_at")
    list_filter = ("status",)
    search_fields = ("public_id", "user__phone")


@admin.register(AIUsageQuota)
class AIUsageQuotaAdmin(admin.ModelAdmin):
    list_display = ("user", "period", "tokens_used", "token_limit", "images_used", "image_limit")
    list_filter = ("period",)
    search_fields = ("user__phone",)
