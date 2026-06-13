from rest_framework import serializers

from apps.accounts.models import Address

from .models import MeasurementRequest, Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    service_tariff = serializers.SlugRelatedField(slug_field="code", read_only=True)

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product_name_snapshot",
            "unit_price",
            "quantity",
            "width_cm",
            "height_cm",
            "service_tariff",
            "line_total",
        )


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "order_number",
            "status",
            "subtotal",
            "discount",
            "delivery_fee",
            "total",
            "payment_status",
            "payment_provider",
            "comment",
            "items",
            "created_at",
        )
        read_only_fields = fields


class CheckoutSerializer(serializers.Serializer):
    address_id = serializers.IntegerField(required=False, allow_null=True)
    comment = serializers.CharField(required=False, allow_blank=True, default="")
    payment_provider = serializers.ChoiceField(
        choices=["payme", "click"], required=False, allow_blank=True
    )

    def validate_address_id(self, value):
        if value is None:
            return value
        user = self.context["request"].user
        if not Address.objects.filter(pk=value, user=user).exists():
            raise serializers.ValidationError("Manzil topilmadi.")
        return value


class OrderStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[c[0] for c in Order.STATUS_CHOICES])


class MeasurementRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeasurementRequest
        fields = (
            "id",
            "order",
            "address",
            "preferred_date",
            "time_slot",
            "status",
            "note",
            "created_at",
        )
        read_only_fields = ("id", "status", "created_at")

    def validate_address(self, value):
        user = self.context["request"].user
        if value.user_id != user.id:
            raise serializers.ValidationError("Manzil sizga tegishli emas.")
        return value


class AdminMeasurementSerializer(serializers.ModelSerializer):
    """Staff can reschedule and move a measurement request through its states."""

    class Meta:
        model = MeasurementRequest
        fields = (
            "id",
            "user",
            "order",
            "address",
            "preferred_date",
            "time_slot",
            "status",
            "note",
            "created_at",
        )
        read_only_fields = ("id", "user", "created_at")
