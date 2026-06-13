from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Address
from apps.cart.services import get_or_create_cart
from apps.common.exceptions import BusinessError
from apps.common.permissions import IsStaffRole
from apps.common.throttles import CheckoutThrottle
from apps.payments.services import build_payment_url

from .models import MeasurementRequest, Order
from .serializers import (
    AdminMeasurementSerializer,
    CheckoutSerializer,
    MeasurementRequestSerializer,
    OrderSerializer,
    OrderStatusSerializer,
)
from .services import can_transition, create_order_from_cart


class OrdersView(generics.ListAPIView):
    """GET lists the caller's orders; POST performs checkout from the cart."""

    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Order.objects.prefetch_related("items")
        user = self.request.user
        if user.role in ("manager", "admin"):
            return qs
        return qs.filter(user=user)

    def get_throttles(self):
        if self.request.method == "POST":
            return [CheckoutThrottle()]
        return super().get_throttles()

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        cart = get_or_create_cart(request)
        address = None
        if data.get("address_id"):
            address = Address.objects.get(pk=data["address_id"], user=request.user)

        provider = data.get("payment_provider", "")
        order = create_order_from_cart(
            user=request.user,
            cart=cart,
            address=address,
            comment=data.get("comment", ""),
            payment_provider=provider,
        )

        payload = OrderSerializer(order).data
        if provider:
            payload["payment_url"] = build_payment_url(order, provider)
        return Response(payload, status=status.HTTP_201_CREATED)


class OrderDetail(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "order_number"

    def get_queryset(self):
        qs = Order.objects.prefetch_related("items")
        user = self.request.user
        if user.role in ("manager", "admin"):
            return qs
        return qs.filter(user=user)


class OrderCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_number):
        user = request.user
        qs = Order.objects.all() if user.role == "admin" else Order.objects.filter(user=user)
        order = generics.get_object_or_404(qs, order_number=order_number)
        if order.status not in ("pending", "paid"):
            raise BusinessError("Bu buyurtmani bekor qilib bo'lmaydi.")
        order.status = "cancelled"
        order.save(update_fields=["status", "updated_at"])
        return Response(OrderSerializer(order).data)


class AdminOrderList(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsStaffRole]
    queryset = Order.objects.prefetch_related("items")
    filterset_fields = ["status", "payment_status"]
    search_fields = ["order_number", "user__phone"]


class AdminOrderUpdate(APIView):
    permission_classes = [IsStaffRole]

    def patch(self, request, order_number):
        order = generics.get_object_or_404(Order, order_number=order_number)
        serializer = OrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]
        if not can_transition(order.status, new_status):
            raise BusinessError(f"'{order.status}' dan '{new_status}' ga o'tib bo'lmaydi.")
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
        return Response(OrderSerializer(order).data)


class MeasurementList(generics.ListCreateAPIView):
    serializer_class = MeasurementRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MeasurementRequest.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AdminMeasurementUpdate(generics.RetrieveUpdateAPIView):
    serializer_class = AdminMeasurementSerializer
    permission_classes = [IsStaffRole]
    queryset = MeasurementRequest.objects.all()
