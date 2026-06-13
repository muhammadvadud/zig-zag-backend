from django.urls import path

from .views import ClickWebhook, PaymeWebhook

urlpatterns = [
    path("payments/payme/", PaymeWebhook.as_view(), name="payme-webhook"),
    path("payments/click/", ClickWebhook.as_view(), name="click-webhook"),
]
