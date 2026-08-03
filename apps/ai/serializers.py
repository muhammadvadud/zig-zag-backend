from rest_framework import serializers

from apps.catalog.models import Product

from .models import AIConversation, AIImageGeneration, AIMessage, AIUsageQuota


class AIConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIConversation
        fields = ("id", "title", "is_archived", "created_at")
        read_only_fields = ("id", "created_at")


class AIMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIMessage
        fields = ("id", "role", "content", "created_at")


class MessageCreateSerializer(serializers.Serializer):
    content = serializers.CharField()


class AIImageGenerationSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="public_id", read_only=True)
    result_image = serializers.SerializerMethodField()

    class Meta:
        model = AIImageGeneration
        fields = ("id", "status", "result_image", "cost_credits", "error_message", "created_at")

    def get_result_image(self, obj):
        if not obj.result_image:
            return None
        request = self.context.get("request")
        url = obj.result_image.url
        return request.build_absolute_uri(url) if request else url


class AdminAIUsageSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(source="user.phone", read_only=True)

    class Meta:
        model = AIUsageQuota
        fields = (
            "user",
            "phone",
            "period",
            "tokens_used",
            "token_limit",
            "images_used",
            "image_limit",
            "messages_used",
        )


class ImageCreateSerializer(serializers.Serializer):
    source_image = serializers.ImageField(required=False)
    product_id = serializers.IntegerField(required=False)
    prompt = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_source_image(self, value):
        if value.size > 8 * 1024 * 1024:
            raise serializers.ValidationError("Rasm hajmi 8MB dan oshmasligi kerak.")
        return value

    def validate_product_id(self, value):
        if value and not Product.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError("Mahsulot topilmadi.")
        return value


class TryOnSerializer(serializers.Serializer):
    """Xonangiz rasmiga pardani "kiydirib" ko'rsatish (AI try-on)."""

    image = serializers.ImageField(required=True)
    product_id = serializers.IntegerField(required=False)

    def validate_image(self, value):
        if value.size > 8 * 1024 * 1024:
            raise serializers.ValidationError("Rasm hajmi 8MB dan oshmasligi kerak.")
        return value

    def validate_product_id(self, value):
        if value and not Product.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError("Mahsulot topilmadi.")
        return value


# ─── Admin dashboard serializers ─────────────────────────────────────────────


class AdminConversationListSerializer(serializers.ModelSerializer):
    """Conversation list for admin — includes user info, message count, total tokens."""

    user_phone = serializers.CharField(source="user.phone", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    message_count = serializers.IntegerField(read_only=True)
    total_tokens = serializers.IntegerField(read_only=True)

    class Meta:
        model = AIConversation
        fields = [
            "id",
            "user_phone",
            "user_name",
            "title",
            "message_count",
            "total_tokens",
            "created_at",
            "updated_at",
        ]


class AdminMessageDetailSerializer(serializers.ModelSerializer):
    """Message detail for admin — includes token counts and model."""

    class Meta:
        model = AIMessage
        fields = [
            "id",
            "role",
            "content",
            "input_tokens",
            "output_tokens",
            "model",
            "created_at",
        ]


class AdminConversationDetailSerializer(serializers.ModelSerializer):
    """Conversation detail with all messages for admin."""

    from django.db.models import Sum

    user_phone = serializers.CharField(source="user.phone", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    messages = AdminMessageDetailSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()
    total_input_tokens = serializers.SerializerMethodField()
    total_output_tokens = serializers.SerializerMethodField()

    class Meta:
        model = AIConversation
        fields = [
            "id",
            "user_phone",
            "user_name",
            "title",
            "message_count",
            "total_input_tokens",
            "total_output_tokens",
            "messages",
            "created_at",
            "updated_at",
        ]

    def get_message_count(self, obj):
        return obj.messages.count()

    def get_total_input_tokens(self, obj):
        from django.db.models import Sum
        return obj.messages.aggregate(total=Sum("input_tokens"))["total"] or 0

    def get_total_output_tokens(self, obj):
        from django.db.models import Sum
        return obj.messages.aggregate(total=Sum("output_tokens"))["total"] or 0


class AdminTokenUsageDetailSerializer(serializers.ModelSerializer):
    """Per-user token usage (AIUsageQuota) for admin dashboard."""

    user_id = serializers.IntegerField(source="user.id", read_only=True)
    user_phone = serializers.CharField(source="user.phone", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    usage_percent = serializers.SerializerMethodField()
    conversation_count = serializers.SerializerMethodField()

    class Meta:
        model = AIUsageQuota
        fields = [
            "user_id",
            "user_phone",
            "user_name",
            "period",
            "tokens_used",
            "token_limit",
            "images_used",
            "image_limit",
            "messages_used",
            "usage_percent",
            "conversation_count",
            "created_at",
            "updated_at",
        ]

    def get_usage_percent(self, obj):
        if not obj.token_limit:
            return 0
        return round((obj.tokens_used / obj.token_limit) * 100, 1)

    def get_conversation_count(self, obj):
        return AIConversation.objects.filter(user=obj.user).count()

