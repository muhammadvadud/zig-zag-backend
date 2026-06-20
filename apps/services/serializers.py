from rest_framework import serializers

from .models import ServiceTariff


class ServiceTariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceTariff
        fields = (
            "code",
            "name",
            "price",
            "price_per_m2",
            "is_popular",
            "features",
        )
