from rest_framework import generics
from rest_framework.permissions import AllowAny

from apps.common.permissions import IsAdminRole

from .models import ServiceTariff
from .serializers import AdminServiceTariffSerializer, ServiceTariffSerializer


class ServiceTariffList(generics.ListAPIView):
    queryset = ServiceTariff.objects.filter(is_active=True)
    serializer_class = ServiceTariffSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class AdminServiceTariffList(generics.ListCreateAPIView):
    serializer_class = AdminServiceTariffSerializer
    permission_classes = [IsAdminRole]
    pagination_class = None
    queryset = ServiceTariff.objects.all()


class AdminServiceTariffDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AdminServiceTariffSerializer
    permission_classes = [IsAdminRole]
    queryset = ServiceTariff.objects.all()
