from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import ServiceTariff
from .serializers import ServiceTariffSerializer


class ServiceTariffList(generics.ListAPIView):
    queryset = ServiceTariff.objects.filter(is_active=True)
    serializer_class = ServiceTariffSerializer
    permission_classes = [AllowAny]
    pagination_class = None
