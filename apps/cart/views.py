from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Color, ProductVariant
from apps.common.exceptions import Conflict
from apps.services.models import ServiceTariff

from .models import CartItem
from .serializers import (
    CartItemUpdateSerializer,
    CartItemWriteSerializer,
    CartSerializer,
)
from .services import get_or_create_cart


class CartView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cart = get_or_create_cart(request)
        return Response(CartSerializer(cart, context={"request": request}).data)


class CartItemCreateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CartItemWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        cart = get_or_create_cart(request)
        variant = ProductVariant.objects.select_related("product").get(pk=data["variant_id"])
        if variant.product.stock < data["quantity"]:
            raise Conflict("Stok yetarli emas.")

        tariff = None
        if data.get("service_tariff"):
            tariff = ServiceTariff.objects.get(code=data["service_tariff"])

        color = None
        if data.get("color_id"):
            color = Color.objects.get(pk=data["color_id"])

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            variant=variant,
            color=color,
            width_cm=data.get("width_cm"),
            height_cm=data.get("height_cm"),
            service_tariff=tariff,
            defaults={"quantity": data["quantity"]},
        )
        if not created:
            item.quantity += data["quantity"]
            item.save(update_fields=["quantity", "updated_at"])

        return Response(
            CartSerializer(cart, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class CartItemDetailView(APIView):
    permission_classes = [AllowAny]

    def _get_item(self, request, pk):
        cart = get_or_create_cart(request)
        try:
            return cart.items.select_related("variant").get(pk=pk)
        except CartItem.DoesNotExist:
            raise PermissionDenied("Bu element sizning savatingizda emas.")

    def patch(self, request, pk):
        item = self._get_item(request, pk)
        serializer = CartItemUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if "quantity" in data:
            if item.variant.product.stock < data["quantity"]:
                raise Conflict("Stok yetarli emas.")
            item.quantity = data["quantity"]
        if "width_cm" in data:
            item.width_cm = data["width_cm"]
        if "height_cm" in data:
            item.height_cm = data["height_cm"]
        if "service_tariff" in data:
            code = data["service_tariff"]
            item.service_tariff = (
                ServiceTariff.objects.filter(code=code, is_active=True).first() if code else None
            )
        item.save()
        return Response(CartSerializer(item.cart, context={"request": request}).data)

    def delete(self, request, pk):
        item = self._get_item(request, pk)
        cart = item.cart
        item.delete()
        return Response(CartSerializer(cart, context={"request": request}).data)
