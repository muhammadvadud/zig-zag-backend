from rest_framework import serializers

from apps.accounts.models import Address

from .models import MeasurementRequest, Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="variant.product.id", read_only=True)
    product_slug = serializers.CharField(source="variant.product.slug", read_only=True)
    variant_id = serializers.IntegerField(source="variant.id", read_only=True)
    color = serializers.CharField(source="color.name", read_only=True, default=None)
    color_hex = serializers.CharField(source="color.hex", read_only=True, default=None)
    image = serializers.SerializerMethodField()
    review = serializers.SerializerMethodField()

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
            "line_total",
            "review",
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

    def get_review(self, obj):
        """Foydalanuvchining shu mahsulotga qoldirgan sharhi (bo'lsa) — buyurtmalar
        ro'yxatida 'Sharh qoldirish' yoki 'Sharhni o'zgartirish'ni ko'rsatish uchun."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        review = next(
            (
                r
                for r in obj.variant.product.reviews.all()
                if r.user_id == request.user.id
            ),
            None,
        )
        if not review:
            return None
        return {
            "id": review.id,
            "rating": review.rating,
            "rating_tailor": review.rating_tailor,
            "rating_service": review.rating_service,
            "comment": review.comment,
            "is_published": review.is_published,
        }


class OrderAddressSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    city = serializers.CharField(source="region", read_only=True)
    district = serializers.CharField(source="city", read_only=True)
    address = serializers.SerializerMethodField()
    landmark = serializers.CharField(read_only=True)

    def get_address(self, obj):
        return " ".join(part for part in (obj.street, obj.home) if part)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer = serializers.SerializerMethodField()
    recipient = serializers.SerializerMethodField()
    service_tariff = serializers.SlugRelatedField(slug_field="code", read_only=True)
    address = OrderAddressSerializer(read_only=True)

    class Meta:
        model = Order
        fields = (
            "order_number",
            "customer",
            "recipient",
            "service_tariff",
            "delivery_method",
            "address",
            "status",
            "subtotal",
            "discount",
            "delivery_fee",
            "total",
            "payment_status",
            "payment_provider",
            "viewed_order",
            "comment",
            "items",
            "created_at",
        )
        read_only_fields = fields

    def get_customer(self, obj):
        return {
            "full_name": obj.user.full_name,
            "phone": obj.user.phone,
        }

    def get_recipient(self, obj):
        if not obj.recipient_phone:
            return None
        return {
            "full_name": obj.recipient_full_name,
            "phone": obj.recipient_phone,
        }


class AdminOrderRowSerializer(serializers.ModelSerializer):
    """Compact order row for the admin list (no nested items)."""

    customer = serializers.SerializerMethodField()
    recipient = serializers.SerializerMethodField()
    service_tariff = serializers.SlugRelatedField(slug_field="code", read_only=True)
    items_count = serializers.IntegerField(source="items.count", read_only=True)

    class Meta:
        model = Order
        fields = (
            "order_number",
            "customer",
            "recipient",
            "service_tariff",
            "items_count",
            "status",
            "payment_status",
            "payment_provider",
            "viewed_order",
            "subtotal",
            "discount",
            "delivery_fee",
            "total",
            "created_at",
        )
        read_only_fields = fields

    def get_customer(self, obj):
        return {
            "full_name": obj.user.full_name,
            "phone": obj.user.phone,
        }

    def get_recipient(self, obj):
        if not obj.recipient_phone:
            return None
        return {
            "full_name": obj.recipient_full_name,
            "phone": obj.recipient_phone,
        }


class RecipientSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=False, allow_blank=True, max_length=150, default="")
    phone = serializers.CharField(max_length=20)


class ManualAddressSerializer(serializers.Serializer):
    city = serializers.CharField(max_length=100)
    district = serializers.CharField(max_length=100)
    address = serializers.CharField(max_length=355)
    landmark = serializers.CharField(required=False, allow_blank=True, max_length=255, default="")


class CheckoutSerializer(serializers.Serializer):
    delivery_method = serializers.ChoiceField(
        choices=[choice[0] for choice in Order.DELIVERY_METHOD_CHOICES], default="postal"
    )
    address_id = serializers.IntegerField(required=False, allow_null=True)
    manual_address = ManualAddressSerializer(required=False)
    comment = serializers.CharField(required=False, allow_blank=True, default="")
    payment_provider = serializers.ChoiceField(
        choices=["payme", "click"], required=False, allow_blank=True
    )
    recipient = RecipientSerializer(required=False, allow_null=True)

    def validate_address_id(self, value):
        if value is None:
            return value
        user = self.context["request"].user
        if not Address.objects.filter(pk=value, user=user).exists():
            raise serializers.ValidationError("Manzil topilmadi.")
        return value

    def validate(self, attrs):
        delivery_method = attrs["delivery_method"]
        address_id = attrs.get("address_id")
        manual_address = attrs.get("manual_address")

        if delivery_method == "pickup":
            if address_id is not None or manual_address is not None:
                raise serializers.ValidationError(
                    "O'zingiz olib ketishda manzil kiritilmaydi."
                )
            return attrs

        if address_id is None and manual_address is None:
            raise serializers.ValidationError(
                {"address": "Pochta orqali yuborish uchun manzil majburiy."}
            )
        if address_id is not None and manual_address is not None:
            raise serializers.ValidationError(
                {"address": "Saqlangan yoki qo'lda kiritilgan manzildan bittasini tanlang."}
            )
        return attrs


class OrderStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[c[0] for c in Order.STATUS_CHOICES], required=False)
    viewed_order = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if "status" not in attrs and "viewed_order" not in attrs:
            raise serializers.ValidationError("Kamida status yoki viewed_order yuborilishi kerak.")
        return attrs


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
