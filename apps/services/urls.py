from django.urls import path

from .views import ServiceTariffList

urlpatterns = [
    path("tariffs/", ServiceTariffList.as_view(), name="tariff-list"),
]
