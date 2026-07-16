from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.cart.services import merge_session_cart

from apps.common.permissions import IsStaffRole

from .models import Address, User
from .serializers import (
    AddressSerializer,
    AdminUserSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    ProfileSerializer,
)
from .services import can_request_otp, generate_otp, verify_otp
from .throttles import OTPRequestThrottle


def issue_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class OTPRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPRequestThrottle]

    @extend_schema(request=OTPRequestSerializer, responses={200: dict})
    def post(self, request):
        from django.conf import settings

        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]
        purpose = serializer.validated_data["purpose"]

        if not can_request_otp(phone):
            return Response(
                {"error": {"code": "throttled", "message": "Iltimos, biroz kuting."}},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        code = generate_otp(phone, purpose)
        payload = {
            "message": "Kod yuborildi",
            "expires_in": settings.OTP_TTL_SECONDS,
            "retry_after": settings.OTP_REQUEST_COOLDOWN,
        }
        if settings.OTP_DEBUG_RETURN_CODE:
            payload["debug_code"] = code
        return Response(payload)


class OTPVerifyView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=OTPVerifySerializer, responses={200: dict})
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]
        code = serializer.validated_data["code"]
        purpose = serializer.validated_data["purpose"]

        if not verify_otp(phone, code, purpose):
            return Response(
                {"error": {"code": "invalid_otp", "message": "Kod noto'g'ri yoki muddati o'tgan."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user, _ = User.objects.get_or_create(
            phone=phone, defaults={"is_phone_verified": True}
        )
        if not user.is_phone_verified:
            user.is_phone_verified = True
            user.save(update_fields=["is_phone_verified"])

        # Merge the anonymous (session) cart into the user's cart on login.
        session_key = request.session.session_key
        if session_key:
            merge_session_cart(session_key, user)

        tokens = issue_tokens(user)
        tokens["user"] = ProfileSerializer(user).data
        return Response(tokens)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response(
                {"error": {"code": "validation_error", "message": "refresh majburiy."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(refresh).blacklist()
        except TokenError:
            return Response(
                {"error": {"code": "invalid_token", "message": "Token yaroqsiz."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class AddressViewSetList(generics.ListCreateAPIView):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AddressDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class AdminUserList(generics.ListAPIView):
    serializer_class = AdminUserSerializer
    permission_classes = [IsStaffRole]
    queryset = User.objects.all().order_by("-date_joined")
    filterset_fields = ["role", "is_active"]
    search_fields = ["phone", "full_name", "email"]


class AdminUserDetail(generics.RetrieveUpdateAPIView):
    serializer_class = AdminUserSerializer
    permission_classes = [IsStaffRole]
    queryset = User.objects.all()
