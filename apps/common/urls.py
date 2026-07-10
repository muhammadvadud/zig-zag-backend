from django.urls import path

from .stats_views import (
    AIUsageStats,
    OrdersByStatusStats,
    OverviewStats,
    PaymentsStats,
    PendingReviewsStats,
    ProductStatsList,
    RecentMeasurementsStats,
    RecentOrdersStats,
    SalesStats,
    TopCategoriesStats,
    TopProductsStats,
)

urlpatterns = [
    path("admin/stats/overview/", OverviewStats.as_view(), name="admin-stats-overview"),
    path("admin/stats/sales/", SalesStats.as_view(), name="admin-stats-sales"),
    path(
        "admin/stats/orders-by-status/",
        OrdersByStatusStats.as_view(),
        name="admin-stats-orders-by-status",
    ),
    path("admin/stats/top-products/", TopProductsStats.as_view(), name="admin-stats-top-products"),
    path("admin/stats/products/", ProductStatsList.as_view(), name="admin-stats-products"),
    path(
        "admin/stats/top-categories/",
        TopCategoriesStats.as_view(),
        name="admin-stats-top-categories",
    ),
    path("admin/stats/payments/", PaymentsStats.as_view(), name="admin-stats-payments"),
    path("admin/stats/ai-usage/", AIUsageStats.as_view(), name="admin-stats-ai-usage"),
    path(
        "admin/stats/recent-orders/",
        RecentOrdersStats.as_view(),
        name="admin-stats-recent-orders",
    ),
    path(
        "admin/stats/pending-reviews/",
        PendingReviewsStats.as_view(),
        name="admin-stats-pending-reviews",
    ),
    path(
        "admin/stats/recent-measurements/",
        RecentMeasurementsStats.as_view(),
        name="admin-stats-recent-measurements",
    ),
]
