from rest_framework import serializers

from apps.common.utils import current_language

from .models import ServiceTariff


class ServiceTariffSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    features = serializers.SerializerMethodField()

    class Meta:
        model = ServiceTariff
        fields = (
            "code",
            "name",
            "price",
            "price_per_m2",
            "is_popular",
            "features",
            "ai_chat_enabled",
            "ai_image_enabled",
        )

    def _lang(self):
        request = self.context.get("request")
        return current_language(request) if request else "uz"

    def get_name(self, obj):
        return obj.name(self._lang())

    def get_features(self, obj):
        return obj.features_for(self._lang())
