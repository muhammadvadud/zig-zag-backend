"""Admin dashboard statistics endpoints (admin-only).

All endpoints live under ``/admin/stats/`` and return plain JSON where
numbers are real numbers (money included) so the dashboard can chart them
without parsing strings.
"""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, F, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.ai.models import AIConversation, AIImageGeneration, AIMessage, AIUsageQuota
from apps.catalog.models import Product, Review
from apps.orders.models import MeasurementRequest, Order, OrderItem
from apps.payments.models import Payment

from .permissions import IsAdminRole

STATUS_LABELS = {
    "pending": "Kutilmoqda",
    "paid": "To'langan",
    "processing": "Jarayonda",
    "measuring": "O'lchovda",
    "sewing": "Tikuvda",
    "shipped": "Jo'natildi",
    "completed": "Yakunlangan",
    "cancelled": "Bekor qilingan",
    "refunded": "Qaytarilgan",
}

PENDING_STATUSES = ["pending", "processing", "measuring", "sewing"]


def _num(value):
    """Coerce a Decimal/None into a plain JSON number (float or int)."""
    if value is None:
        return 0
    if isinstance(value, Decimal):
        return float(value)
    return value


def _pct(current, previous):
    """Percentage change of current vs previous, guarded against zero."""
    current = float(current or 0)
    previous = float(previous or 0)
    if previous == 0:
        return 0
    return round((current - previous) / previous * 100, 1)


class AdminStatsBase(APIView):
    permission_classes = [IsAdminRole]


class OverviewStats(AdminStatsBase):
    def get(self, request):
        now = timezone.localtime()
        today = now.date()
        yesterday = today - timedelta(days=1)
        month_start = today.replace(day=1)
        prev_month_end = month_start - timedelta(days=1)
        prev_month_start = prev_month_end.replace(day=1)

        paid = Order.objects.filter(payment_status="paid")

        today_sales = paid.filter(created_at__date=today).aggregate(s=Sum("total"))["s"]
        yest_sales = paid.filter(created_at__date=yesterday).aggregate(s=Sum("total"))["s"]
        month_sales = paid.filter(created_at__date__gte=month_start).aggregate(s=Sum("total"))["s"]
        prev_month_sales = paid.filter(
            created_at__date__gte=prev_month_start, created_at__date__lte=prev_month_end
        ).aggregate(s=Sum("total"))["s"]

        orders_today = Order.objects.filter(created_at__date=today).count()
        orders_yest = Order.objects.filter(created_at__date=yesterday).count()
        orders_month = Order.objects.filter(created_at__date__gte=month_start).count()
        orders_prev_month = Order.objects.filter(
            created_at__date__gte=prev_month_start, created_at__date__lte=prev_month_end
        ).count()

        avg_check = paid.aggregate(a=Avg("total"))["a"]
        new_customers_month = User.objects.filter(
            role="customer", date_joined__date__gte=month_start
        ).count()
        pending_orders = Order.objects.filter(status__in=PENDING_STATUSES).count()
        measurement_requests = MeasurementRequest.objects.filter(status="requested").count()

        # Conversion = orders placed vs. carts ever started. Carts that became
        # orders no longer exist as Cart rows, so the denominator is the active
        # (abandoned) carts plus the orders themselves. Bounded to [0, 100].
        orders_total = Order.objects.count()
        active_carts = self._cart_total()
        denom = orders_total + active_carts
        conversion = round(orders_total / denom * 100, 1) if denom else 0.0

        return Response(
            {
                "today_sales": _num(today_sales),
                "month_sales": _num(month_sales),
                "orders_today": orders_today,
                "orders_month": orders_month,
                "avg_check": round(_num(avg_check), 2),
                "new_customers_month": new_customers_month,
                "pending_orders": pending_orders,
                "measurement_requests": measurement_requests,
                "conversion": conversion,
                "deltas": {
                    "today_sales_pct": _pct(today_sales, yest_sales),
                    "month_sales_pct": _pct(month_sales, prev_month_sales),
                    "orders_pct": _pct(orders_month, orders_prev_month),
                },
            }
        )

    @staticmethod
    def _cart_total():
        try:
            from apps.cart.models import Cart

            return Cart.objects.count()
        except Exception:
            return 0


class SalesStats(AdminStatsBase):
    def get(self, request):
        try:
            days = int(request.query_params.get("days", 30))
        except (TypeError, ValueError):
            days = 30
        days = max(1, min(days, 365))

        end = timezone.localtime().date()
        start = end - timedelta(days=days - 1)

        rows = (
            Order.objects.filter(payment_status="paid", created_at__date__gte=start)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(revenue=Sum("total"), orders=Count("id"))
        )
        by_day = {r["day"]: r for r in rows}

        points = []
        for i in range(days):
            d = start + timedelta(days=i)
            row = by_day.get(d)
            points.append(
                {
                    "date": d.isoformat(),
                    "revenue": _num(row["revenue"]) if row else 0,
                    "orders": row["orders"] if row else 0,
                }
            )
        return Response({"points": points})


class OrdersByStatusStats(AdminStatsBase):
    def get(self, request):
        rows = (
            Order.objects.values("status")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        items = [
            {
                "status": r["status"],
                "label": STATUS_LABELS.get(r["status"], r["status"]),
                "count": r["count"],
            }
            for r in rows
        ]
        return Response({"items": items})


class TopProductsStats(AdminStatsBase):
    def get(self, request):
        try:
            limit = int(request.query_params.get("limit", 10))
        except (TypeError, ValueError):
            limit = 10
        limit = max(1, min(limit, 100))

        rows = (
            OrderItem.objects.values("variant__product")
            .annotate(
                name=F("variant__product__name"),
                qty=Sum("quantity"),
                revenue=Sum("line_total"),
            )
            .order_by("-revenue")[:limit]
        )
        items = [
            {
                "product_id": r["variant__product"],
                "name": r["name"],
                "qty": r["qty"] or 0,
                "revenue": _num(r["revenue"]),
            }
            for r in rows
        ]
        return Response({"items": items})


class TopCategoriesStats(AdminStatsBase):
    def get(self, request):
        rows = (
            OrderItem.objects.values("variant__product__category")
            .annotate(
                category=F("variant__product__category__slug"),
                name=F("variant__product__category__name"),
                qty=Sum("quantity"),
                revenue=Sum("line_total"),
            )
            .order_by("-revenue")
        )
        items = [
            {
                "category": r["category"],
                "name": r["name"],
                "revenue": _num(r["revenue"]),
                "qty": r["qty"] or 0,
            }
            for r in rows
        ]
        return Response({"items": items})


class PaymentsStats(AdminStatsBase):
    def get(self, request):
        rows = (
            Payment.objects.filter(state=Payment.STATE_COMPLETED)
            .values("provider")
            .annotate(amount=Sum("amount"), count=Count("id"))
            .order_by("-amount")
        )
        items = [
            {"provider": r["provider"], "amount": _num(r["amount"]), "count": r["count"]}
            for r in rows
        ]
        if not items:
            rows = (
                Order.objects.filter(payment_status="paid")
                .exclude(payment_provider="")
                .values("payment_provider")
                .annotate(amount=Sum("total"), count=Count("id"))
                .order_by("-amount")
            )
            items = [
                {
                    "provider": r["payment_provider"],
                    "amount": _num(r["amount"]),
                    "count": r["count"],
                }
                for r in rows
            ]
        return Response({"items": items})


class AIUsageStats(AdminStatsBase):
    def get(self, request):
        period = request.query_params.get("period") or timezone.localtime().strftime("%Y-%m")

        quota = AIUsageQuota.objects.filter(period=period).aggregate(
            tokens=Sum("tokens_used"),
            images=Sum("images_used"),
            messages=Sum("messages_used"),
        )
        tokens_used = quota["tokens"] or 0
        images_used = quota["images"] or 0
        messages_used = quota["messages"] or 0

        # Fall back to raw counters when quota rows are absent.
        msg_qs = AIMessage.objects.filter(created_at__year=period[:4], created_at__month=period[5:7])
        if not messages_used:
            messages_used = msg_qs.count()
        if not tokens_used:
            agg = msg_qs.aggregate(
                t=Sum("input_tokens"), o=Sum("output_tokens")
            )
            tokens_used = (agg["t"] or 0) + (agg["o"] or 0)
        if not images_used:
            images_used = AIImageGeneration.objects.filter(
                created_at__year=period[:4], created_at__month=period[5:7]
            ).count()

        conversations = AIConversation.objects.filter(
            created_at__year=period[:4], created_at__month=period[5:7]
        ).count()

        top_users = list(
            AIUsageQuota.objects.filter(period=period, tokens_used__gt=0)
            .values("user")
            .annotate(name=F("user__full_name"), phone=F("user__phone"), tokens=Sum("tokens_used"))
            .order_by("-tokens")[:10]
        )
        top_users = [
            {
                "user_id": r["user"],
                "name": r["name"] or r["phone"],
                "tokens": r["tokens"],
            }
            for r in top_users
        ]

        return Response(
            {
                "tokens_used": tokens_used,
                "images_used": images_used,
                "messages_used": messages_used,
                "conversations": conversations,
                "top_users": top_users,
            }
        )


class LowStockStats(AdminStatsBase):
    def get(self, request):
        try:
            threshold = int(request.query_params.get("threshold", 10))
        except (TypeError, ValueError):
            threshold = 10

        rows = (
            Product.objects.filter(stock__lt=threshold)
            .order_by("stock")
            .values("id", "name", "slug", "stock")
        )
        items = [
            {"id": r["id"], "name": r["name"], "slug": r["slug"], "stock": r["stock"]}
            for r in rows
        ]
        return Response({"items": items})


class RecentOrdersStats(AdminStatsBase):
    def get(self, request):
        try:
            limit = int(request.query_params.get("limit", 10))
        except (TypeError, ValueError):
            limit = 10
        limit = max(1, min(limit, 100))

        orders = (
            Order.objects.select_related("user").order_by("-created_at")[:limit]
        )
        items = [
            {
                "order_number": o.order_number,
                "customer": o.user.full_name or o.user.phone,
                "status": o.status,
                "payment_status": o.payment_status,
                "total": _num(o.total),
                "created_at": o.created_at.isoformat(),
            }
            for o in orders
        ]
        return Response({"items": items})


class PendingReviewsStats(AdminStatsBase):
    def get(self, request):
        try:
            limit = int(request.query_params.get("limit", 10))
        except (TypeError, ValueError):
            limit = 10
        limit = max(1, min(limit, 100))

        reviews = (
            Review.objects.filter(is_published=False)
            .select_related("product", "user")
            .order_by("-created_at")[:limit]
        )
        items = [
            {
                "id": r.id,
                "product": r.product.name,
                "user_name": r.user.full_name or r.user.phone,
                "rating": r.rating,
                "comment": r.comment,
                "created_at": r.created_at.isoformat(),
            }
            for r in reviews
        ]
        return Response({"items": items})


class RecentMeasurementsStats(AdminStatsBase):
    def get(self, request):
        try:
            limit = int(request.query_params.get("limit", 10))
        except (TypeError, ValueError):
            limit = 10
        limit = max(1, min(limit, 100))

        rows = (
            MeasurementRequest.objects.select_related("user").order_by("-created_at")[:limit]
        )
        items = [
            {
                "id": m.id,
                "customer": m.user.full_name or m.user.phone,
                "preferred_date": m.preferred_date.isoformat(),
                "time_slot": m.time_slot,
                "status": m.status,
            }
            for m in rows
        ]
        return Response({"items": items})
