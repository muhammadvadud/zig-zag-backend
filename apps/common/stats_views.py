"""Admin dashboard statistics endpoints (admin-only).

All endpoints live under ``/admin/stats/`` and return plain JSON where
numbers are real numbers (money included) so the dashboard can chart them
without parsing strings.
"""

from datetime import timedelta
from decimal import Decimal

from django.db.models import (
    Avg,
    Case,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    FloatField,
    IntegerField,
    OuterRef,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone
from rest_framework import generics, serializers
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.ai.models import AIConversation, AIImageGeneration, AIMessage, AIUsageQuota
from apps.catalog.models import Favorite, Product, ProductView, Review
from apps.orders.models import MeasurementRequest, Order, OrderItem
from apps.payments.models import Payment

from .pagination import StandardPagination
from .permissions import IsStaffRole

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

# "Sotilgan" deb hisoblanadigan holatlar — to'lov qabul qilingandan keyingi
# barcha bosqichlar (pending/cancelled/refunded bundan mustasno). `Order.status`
# vaqtning bir nuqtasidagi holat (tarix emas) bo'lgani uchun faqat 'paid'ni emas,
# undan keyingi ishlab chiqarish bosqichlarini ham qo'shish kerak — aks holda
# "processing"/"sewing" holatidagi (allaqachon to'langan) buyurtmalar tushum va
# sotuv statistikasidan tushib qolib, raqamlar kamroq chiqadi.
SOLD_STATUSES = ["paid", "processing", "measuring", "sewing", "shipped", "completed"]


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
    permission_classes = [IsStaffRole]


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

        # Umumiy (davrga bog'liq bo'lmagan) raqamlar — mahsulot statistikasi
        # sahifasining yuqori KPI qatori uchun.
        total_products = Product.objects.filter(is_deleted=False).count()
        total_views = Product.objects.aggregate(v=Sum("views_count"))["v"]
        total_revenue = Order.objects.filter(status__in=SOLD_STATUSES).aggregate(v=Sum("total"))["v"]
        total_customers = User.objects.filter(role="customer").count()

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
                # Katalog bo'yicha umumiy KPI (Mahsulot statistikasi sahifasi uchun):
                "products": total_products,
                "total_views": _num(total_views),
                "total_orders": orders_total,
                "total_revenue": _num(total_revenue),
                "total_customers": total_customers,
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


# --------------------------------------------------------------------------- #
# Per-product statistics (views / sales / revenue / conversion)
# --------------------------------------------------------------------------- #


def _top_variants_for(products):
    """product_id -> {"name", "sold_qty"} for the best-selling variant of each
    product (or absent if the product never sold). One query for the whole page."""

    product_ids = [p.id for p in products]
    if not product_ids:
        return {}
    rows = (
        OrderItem.objects.filter(
            variant__product_id__in=product_ids, order__status__in=SOLD_STATUSES
        )
        .values(
            "variant__product_id",
            "variant_id",
            "variant__name",
            "variant__width_cm",
            "variant__height_cm",
        )
        .annotate(qty=Sum("quantity"))
        .order_by("variant__product_id", "-qty")
    )
    top = {}
    for row in rows:
        pid = row["variant__product_id"]
        if pid in top:
            continue  # birinchi qator = shu mahsulot uchun eng ko'p sotilgan variant
        width, height = row["variant__width_cm"], row["variant__height_cm"]
        name = row["variant__name"] or (
            f"{width}×{height} sm" if width and height else f"#{row['variant_id']}"
        )
        top[pid] = {"name": name, "sold_qty": row["qty"] or 0}
    return top


class AliasOrderingFilter(OrderingFilter):
    """OrderingFilter that accepts public *aliases* in ``?ordering=`` and maps
    them to the real (annotated) queryset field names before ordering.

    Dashboard API kontrakti alias yuboradi (``views, sales, revenue, ...``),
    lekin queryset'dagi haqiqiy maydonlar boshqacha nomlanadi (``views_count,
    sold_qty, ...``). DRF'ning standart ``OrderingFilter``i ``ordering_fields``
    tuple'ining BIRINCHI elementini (haqiqiy maydon nomini) qabul qiladi, alias
    (ikkinchi element) esa faqat ko'rsatish uchun — shuning uchun alias bilan
    kelgan ``?ordering=`` jim rad etilib, default'ga tushib qolardi. Bu filtr
    alias'ni haqiqiy maydonga o'giradi. View ``ordering_alias_map`` e'lon qiladi.
    """

    def get_ordering(self, request, queryset, view):
        params = request.query_params.get(self.ordering_param)
        alias_map = getattr(view, "ordering_alias_map", {}) or {}
        if params:
            ordering = []
            for term in params.split(","):
                term = term.strip()
                if not term:
                    continue
                desc = term.startswith("-")
                alias = term[1:] if desc else term
                real = alias_map.get(alias)
                if real:
                    ordering.append(("-" if desc else "") + real)
            if ordering:
                return ordering
        return self.get_default_ordering(view)


class ProductStatsSerializer(serializers.Serializer):
    """Row shape for GET /admin/stats/products/ — see annotations on the queryset
    in ProductStatsList.get_queryset for where every number comes from."""

    id = serializers.IntegerField()
    slug = serializers.CharField()
    name = serializers.CharField()
    main_image = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    views_count = serializers.IntegerField()
    views_7d = serializers.IntegerField()
    views_30d = serializers.IntegerField()
    favorites_count = serializers.IntegerField()
    orders_count = serializers.IntegerField()
    sold_qty = serializers.IntegerField()
    revenue = serializers.SerializerMethodField()
    reviews_count = serializers.IntegerField()
    rating_avg = serializers.DecimalField(max_digits=3, decimal_places=2)
    conversion = serializers.SerializerMethodField()
    top_variant = serializers.SerializerMethodField()

    def get_revenue(self, obj):
        return _num(obj.revenue)

    def get_conversion(self, obj):
        # 0..1 nisbat (front foizga o'zi ko'paytiradi) — masalan 0.0834 = 8.34%.
        return round(float(obj.conversion or 0), 4)

    def get_category(self, obj):
        return obj.category.slug if obj.category_id else None

    def get_main_image(self, obj):
        imgs = list(obj.images.all())
        main = next((i for i in imgs if i.is_main), None) or (imgs[0] if imgs else None)
        if not main:
            return None
        request = self.context.get("request")
        url = main.image.url
        return request.build_absolute_uri(url) if request else url

    def get_top_variant(self, obj):
        top_variants = self.context.get("top_variants") or {}
        return top_variants.get(obj.id)


class ProductStatsList(generics.ListAPIView):
    """Paginated per-product analytics table for the admin dashboard.

    ?category=<slug>  — filter by category
    ?search=<text>    — matches product name (uz/ru)
    ?ordering=<field>  where field in
        views | sales | revenue | favorites | rating | conversion
        (prefix with "-" for descending, e.g. ?ordering=-revenue)
    """

    serializer_class = ProductStatsSerializer
    permission_classes = [IsStaffRole]
    pagination_class = StandardPagination
    filter_backends = [SearchFilter, AliasOrderingFilter]
    search_fields = ["name_uz", "name_ru"]
    # Dashboard yuboradigan alias -> queryset'dagi haqiqiy annotatsiya maydoni.
    ordering_alias_map = {
        "views": "views_count",
        "sales": "sold_qty",
        "revenue": "revenue",
        "favorites": "favorites_count",
        "rating": "rating_avg",
        "conversion": "conversion",
    }
    ordering = ["-views_count"]

    def get_queryset(self):
        now = timezone.now()
        d7 = now - timedelta(days=7)
        d30 = now - timedelta(days=30)

        # Product has several independent reverse relations (order items,
        # favorites, review, view logs). Aggregating them together in a single
        # annotate() call would JOIN all of them at once and multiply rows across
        # relations, inflating every Count/Sum (Django's well-known aggregation
        # "fan-out" problem — see the ORM docs' "combining multiple aggregations"
        # warning). Each metric is therefore computed as its own correlated
        # Subquery so the numbers stay correct regardless of how many rows the
        # other relations have.
        sold_items = OrderItem.objects.filter(
            variant__product=OuterRef("pk"), order__status__in=SOLD_STATUSES
        )
        sold_qty_sq = sold_items.values("variant__product").annotate(v=Sum("quantity")).values("v")
        revenue_sq = sold_items.values("variant__product").annotate(v=Sum("line_total")).values("v")
        orders_count_sq = (
            sold_items.values("variant__product").annotate(v=Count("order", distinct=True)).values("v")
        )
        favorites_sq = (
            Favorite.objects.filter(product=OuterRef("pk"))
            .values("product").annotate(v=Count("id")).values("v")
        )
        reviews_sq = (
            Review.objects.filter(product=OuterRef("pk"), is_published=True)
            .values("product").annotate(v=Count("id")).values("v")
        )
        views7_sq = (
            ProductView.objects.filter(product=OuterRef("pk"), created_at__gte=d7)
            .values("product").annotate(v=Count("id")).values("v")
        )
        views30_sq = (
            ProductView.objects.filter(product=OuterRef("pk"), created_at__gte=d30)
            .values("product").annotate(v=Count("id")).values("v")
        )

        qs = (
            Product.objects.filter(is_deleted=False)
            .select_related("category")
            .prefetch_related("images")
            .annotate(
                sold_qty=Coalesce(Subquery(sold_qty_sq, output_field=IntegerField()), 0),
                revenue=Coalesce(
                    Subquery(revenue_sq, output_field=DecimalField(max_digits=14, decimal_places=2)),
                    Value(Decimal("0")),
                ),
                orders_count=Coalesce(Subquery(orders_count_sq, output_field=IntegerField()), 0),
                favorites_count=Coalesce(Subquery(favorites_sq, output_field=IntegerField()), 0),
                reviews_count=Coalesce(Subquery(reviews_sq, output_field=IntegerField()), 0),
                views_7d=Coalesce(Subquery(views7_sq, output_field=IntegerField()), 0),
                views_30d=Coalesce(Subquery(views30_sq, output_field=IntegerField()), 0),
            )
            .annotate(
                # orders_count / views_count as a ratio, guarded against divide-by-zero.
                conversion=Case(
                    When(views_count=0, then=Value(0.0)),
                    default=ExpressionWrapper(
                        F("orders_count") * 1.0 / F("views_count"), output_field=FloatField()
                    ),
                    output_field=FloatField(),
                )
            )
        )

        category_slug = self.request.query_params.get("category")
        if category_slug:
            qs = qs.filter(category__slug=category_slug)
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        products = page if page is not None else list(queryset)
        top_variants = _top_variants_for(products)
        serializer = self.get_serializer(
            products, many=True, context={"request": request, "top_variants": top_variants}
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)
