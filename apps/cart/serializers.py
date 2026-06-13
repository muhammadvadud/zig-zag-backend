from rest_framework import serializers

from apps.catalog.models import ProductVariant
from apps.common.utils import current_language
from apps.services.models import ServiceTariff

from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    color = serializers.SerializerMethodField()
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    service_tariff = serializers.SlugRelatedField(slug_field="code", read_only=True)

    class Meta:
        model = CartItem
        fields = (
            "id",
            "variant",
            "product_name",
            "color",
            "unit_price",
            "quantity",
            "width_cm",
            "height_cm",
            "service_tariff",
            "line_total",
        )

    def _lang(self):
        request = self.context.get("request")
        return current_language(request) if request else "uz"

    def get_product_name(self, obj):
        return obj.variant.product.name(self._lang())

    def get_color(self, obj):
        return obj.variant.color.name(self._lang())


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    discount = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ("id", "items", "subtotal", "discount", "total")

    def get_discount(self, obj):
        return 0


class CartItemWriteSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, max_value=50, default=1)
    width_cm = serializers.IntegerField(min_value=10, max_value=1000, required=False, allow_null=True)
    height_cm = serializers.IntegerField(min_value=10, max_value=1000, required=False, allow_null=True)
    service_tariff = serializers.CharField(required=False, allow_null=True)

    def validate_variant_id(self, value):
        if not ProductVariant.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Variant topilmadi.")
        return value

    def validate_service_tariff(self, value):
        if value and not ServiceTariff.objects.filter(code=value, is_active=True).exists():
            raise serializers.ValidationError("Tarif topilmadi.")
        return value


class CartItemUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, max_value=50, required=False)
    width_cm = serializers.IntegerField(min_value=10, max_value=1000, required=False, allow_null=True)
    height_cm = serializers.IntegerField(min_value=10, max_value=1000, required=False, allow_null=True)
    service_tariff = serializers.CharField(required=False, allow_null=True)
