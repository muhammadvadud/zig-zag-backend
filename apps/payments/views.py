from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import click, payme
from .services import ip_allowed


class PaymeWebhook(APIView):
    """Payme Merchant API endpoint (JSON-RPC). Auth + IP allowlist enforced."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        if not ip_allowed(request, settings.PAYME_ALLOWED_IPS):
            return Response(
                {"error": {"code": -32504, "message": "IP ruxsat etilmagan"}}
            )
        result = payme.handle(request, request.data or {})
        return Response(result)


class ClickWebhook(APIView):
    """Click Prepare/Complete endpoint. Signature + IP allowlist enforced."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        if not ip_allowed(request, settings.CLICK_ALLOWED_IPS):
            return Response({"error": click.ERR_SIGN, "error_note": "IP ruxsat etilmagan"})
        result = click.handle(request.data or {})
        return Response(result)
