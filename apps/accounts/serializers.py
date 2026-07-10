import re

from rest_framework import serializers

from .models import Address, User

PHONE_RE = re.compile(r"^\+998\d{9}$")


def validate_phone(value):
    if not PHONE_RE.match(value):
        raise serializers.ValidationError("Telefon raqami noto'g'ri formatda (+998XXXXXXXXX).")
    return value


class OTPRequestSerializer(serializers.Serializer):
    phone = serializers.CharField()
    purpose = serializers.ChoiceField(
        choices=["login", "register", "reset"], default="login"
    )

    def validate_phone(self, value):
        return validate_phone(value)


class OTPVerifySerializer(serializers.Serializer):
    phone = serializers.CharField()
    code = serializers.CharField(min_length=6, max_length=6)
    purpose = serializers.ChoiceField(
        choices=["login", "register", "reset"], default="login"
    )

    def validate_phone(self, value):
        return validate_phone(value)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "phone", "full_name", "email", "role", "language")
        read_only_fields = ("id", "phone", "role")


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "phone",
            "full_name",
            "email",
            "role",
            "language",
            "is_phone_verified",
            "telegram_enabled",
            "date_joined",
        )
        read_only_fields = (
            "id",
            "phone",
            "role",
            "is_phone_verified",
            "telegram_enabled",
            "date_joined",
        )


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "phone",
            "full_name",
            "email",
            "role",
            "is_active",
            "is_phone_verified",
            "language",
            "telegram_enabled",
            "date_joined",
        )
        read_only_fields = ("id", "phone", "date_joined", "is_phone_verified", "telegram_enabled")

    def validate_role(self, value):
        # Admin — dev-only, operatsion ish qilmaydi. Faqat admin o'zi boshqa
        # foydalanuvchiga admin huquqini bera oladi (manager esa emas).
        request = self.context.get("request")
        requester = getattr(request, "user", None)
        if value == "admin" and not (requester and requester.role == "admin"):
            raise serializers.ValidationError(
                "Faqat admin boshqa foydalanuvchiga 'admin' rolini bera oladi."
            )
        return value


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = (
            "id",
            "region",
            "city",
            "street",
            "home",
            "landmark",
            "is_default",
        )
        read_only_fields = ("id",)
