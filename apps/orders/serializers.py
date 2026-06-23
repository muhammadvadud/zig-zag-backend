from rest_framework import serializers

from apps.accounts.models import Address

from .models import MeasurementRequest, Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    service_tariff = serializers.SlugRelatedField(slug_field="code", read_only=True)
    product_id = serializers.IntegerField(source="variant.product.id", read_only=True)
    product_slug = serializers.CharField(source="variant.product.slug", read_only=True)
    variant_id = serializers.IntegerField(source="variant.id", read_only=True)
    color = serializers.CharField(source="variant.color.name", read_only=True)
    color_hex = serializers.CharField(source="variant.color.hex", read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product_id",
            "product_slug",
            "variant_id",
            "product_name_snapshot",
            "color",
            "color_hex",
            "image",
            "unit_price",
            "quantity",
            "width_cm",
            "height_cm",
            "service_tariff",
            "line_total",
        )

    def get_image(self, obj):
        product = obj.variant.product
        imgs = list(product.images.all())
        main = next((i for i in imgs if i.is_main), None) or (imgs[0] if imgs else None)
        if not main:
            return None
        request = self.context.get("request")
        url = main.image.url
        return request.build_absolute_uri(url) if request else url


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "order_number",
            "customer",
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

    def get_customer(self, obj):
        return obj.user.full_name or obj.user.phone


class AdminOrderRowSerializer(serializers.ModelSerializer):
    """Compact order row for the admin list (no nested items)."""

    customer = serializers.SerializerMethodField()
    items_count = serializers.IntegerField(source="items.count", read_only=True)

    class Meta:
        model = Order
        fields = (
            "order_number",
            "customer",
            "items_count",
            "status",
            "payment_status",
            "payment_provider",
            "subtotal",
            "discount",
            "delivery_fee",
            "total",
            "created_at",
        )
        read_only_fields = fields

    def get_customer(self, obj):
        return obj.user.full_name or obj.user.phone


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
