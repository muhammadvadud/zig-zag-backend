from django.db.models import Count, Prefetch
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Review

from apps.accounts.models import Address
from apps.cart.services import get_or_create_cart
from apps.common.exceptions import BusinessError
from apps.common.permissions import IsOrderStaff, IsStaffRole
from apps.common.throttles import CheckoutThrottle
from apps.notifications.services import notify_new_order, notify_status_change
from apps.payments.services import build_payment_url

from .models import MeasurementRequest, Order
from .serializers import (
    AdminMeasurementSerializer,
    AdminOrderRowSerializer,
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
        user = self.request.user
        qs = Order.objects.select_related("user", "address", "service_tariff").prefetch_related(
            "items__variant__product__images",
            "items__color",
            Prefetch(
                "items__variant__product__reviews",
                queryset=Review.objects.filter(user=user),
            ),
        )
        if user.role in ("employee", "manager", "admin"):
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
        elif data.get("manual_address"):
            manual_address = data["manual_address"]
            address = Address.objects.create(
                user=request.user,
                region=manual_address["city"],
                city=manual_address["district"],
                street=manual_address["address"],
                home="",
                landmark=manual_address["landmark"],
            )

        provider = data.get("payment_provider", "")
        recipient = data.get("recipient") or {}
        order = create_order_from_cart(
            user=request.user,
            cart=cart,
            address=address,
            comment=data.get("comment", ""),
            payment_provider=provider,
            recipient_full_name=recipient.get("full_name", ""),
            recipient_phone=recipient.get("phone", ""),
            delivery_method=data["delivery_method"],
        )

        notify_new_order(order)

        payload = OrderSerializer(order, context={"request": request}).data
        if provider:
            payload["payment_url"] = build_payment_url(order, provider)
        return Response(payload, status=status.HTTP_201_CREATED)


class OrderDetail(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "order_number"

    def get_queryset(self):
        user = self.request.user
        qs = Order.objects.select_related("user", "address", "service_tariff").prefetch_related(
            "items__variant__product__images",
            "items__color",
            Prefetch(
                "items__variant__product__reviews",
                queryset=Review.objects.filter(user=user),
            ),
        )
        if user.role in ("employee", "manager", "admin"):
            return qs
        return qs.filter(user=user)


class OrderCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_number):
        user = request.user
        staff = user.role in ("employee", "manager", "admin")
        qs = Order.objects.all() if staff else Order.objects.filter(user=user)
        order = generics.get_object_or_404(qs, order_number=order_number)
        if order.status not in ("pending", "paid"):
            raise BusinessError("Bu buyurtmani bekor qilib bo'lmaydi.")
        order.status = "cancelled"
        order.save(update_fields=["status", "updated_at"])
        return Response(OrderSerializer(order, context={"request": request}).data)


class AdminOrderList(generics.ListAPIView):
    serializer_class = AdminOrderRowSerializer
    permission_classes = [IsOrderStaff]
    queryset = Order.objects.select_related("user", "address", "service_tariff").prefetch_related("items")
    filterset_fields = ["status", "payment_status"]
    search_fields = ["order_number", "user__phone"]

    def get_queryset(self):
        qs = super().get_queryset()
        # Xodim faqat to'lovi tasdiqlangan buyurtmalarni ko'radi — u tikuv/
        # jo'natish oqimi bilan shug'ullanadi, to'lanmagan buyurtma unga
        # tegishli emas. Manager/admin operatsion nazorat uchun hammasini
        # ko'radi (to'lanmaganlarni ham kuzatishi kerak).
        if self.request.user.role == "employee":
            qs = qs.filter(payment_status="paid")
        status_in = self.request.query_params.get("status__in")
        if status_in:
            values = [v.strip() for v in status_in.split(",") if v.strip()]
            if values:
                qs = qs.filter(status__in=values)
        return qs

    def filter_queryset(self, queryset):
        status_in = self.request.query_params.get("status__in")
        if not status_in:
            return super().filter_queryset(queryset)

        # status__in already narrowed the queryset in get_queryset(). If the
        # exact `status` param was also supplied, don't let DjangoFilterBackend
        # AND it back in — status__in takes priority.
        original_get = self.request._request.GET
        if "status" in original_get:
            stripped = original_get.copy()
            stripped.pop("status", None)
            self.request._request.GET = stripped
            try:
                return super().filter_queryset(queryset)
            finally:
                self.request._request.GET = original_get
        return super().filter_queryset(queryset)


class AdminOrderStatusCounts(APIView):
    permission_classes = [IsOrderStaff]

    def get(self, request):
        counts = {status_value: 0 for status_value, _ in Order.STATUS_CHOICES}
        qs = Order.objects.all()
        if request.user.role == "employee":
            qs = qs.filter(payment_status="paid")
        rows = qs.values("status").annotate(n=Count("id"))
        for row in rows:
            counts[row["status"]] = row["n"]
        return Response(counts)


class AdminOrderUpdate(APIView):
    permission_classes = [IsOrderStaff]

    def get(self, request, order_number):
        order = generics.get_object_or_404(
            Order.objects.select_related("user", "address", "service_tariff").prefetch_related(
                "items__variant__product__images", "items__color"
            ),
            order_number=order_number,
        )
        return Response(OrderSerializer(order, context={"request": request}).data)

    def patch(self, request, order_number):
        order = generics.get_object_or_404(Order, order_number=order_number)
        serializer = OrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]
        old_status = order.status
        if not can_transition(old_status, new_status):
            raise BusinessError(f"'{order.status}' dan '{new_status}' ga o'tib bo'lmaydi.")
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
        notify_status_change(order, old_status, new_status)
        return Response(OrderSerializer(order, context={"request": request}).data)


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
