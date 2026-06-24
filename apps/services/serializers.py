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


class AdminServiceTariffSerializer(serializers.ModelSerializer):
    """Full read/write tariff representation for admin management."""

    class Meta:
        model = ServiceTariff
        fields = (
            "id",
            "code",
            "name",
            "price",
            "price_per_m2",
            "is_popular",
            "features",
            "sort_order",
            "is_active",
        )
