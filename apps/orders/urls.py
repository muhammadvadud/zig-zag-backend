from django.urls import path

from .views import (
    AdminMeasurementUpdate,
    AdminOrderList,
    AdminOrderStatusCounts,
    AdminOrderUpdate,
    MeasurementList,
    OrderCancelView,
    OrderDetail,
    OrdersView,
)

urlpatterns = [
    path("orders/", OrdersView.as_view(), name="order-list"),
    path("orders/<str:order_number>/", OrderDetail.as_view(), name="order-detail"),
    path("orders/<str:order_number>/cancel/", OrderCancelView.as_view(), name="order-cancel"),
    path("measurements/", MeasurementList.as_view(), name="measurement-list"),
    # Staff
    path("admin/orders/status-counts/", AdminOrderStatusCounts.as_view(), name="admin-order-status-counts"),
    path("admin/orders/", AdminOrderList.as_view(), name="admin-order-list"),
    path("admin/orders/<str:order_number>/", AdminOrderUpdate.as_view(), name="admin-order-update"),
    path("admin/measurements/<int:pk>/", AdminMeasurementUpdate.as_view(), name="admin-measurement-update"),
]
