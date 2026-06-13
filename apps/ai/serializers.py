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
