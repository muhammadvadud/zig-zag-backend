from django.urls import path

from .views import (
    AdminServiceTariffDetail,
    AdminServiceTariffList,
    ServiceTariffList,
)

urlpatterns = [
    path("tariffs/", ServiceTariffList.as_view(), name="tariff-list"),
    path("admin/tariffs/", AdminServiceTariffList.as_view(), name="admin-tariff-list"),
    path("admin/tariffs/<int:pk>/", AdminServiceTariffDetail.as_view(), name="admin-tariff-detail"),
]
