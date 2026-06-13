from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AddressDetail,
    AddressViewSetList,
    AdminUserDetail,
    AdminUserList,
    LogoutView,
    MeView,
    OTPRequestView,
    OTPVerifyView,
    ProfileView,
)

urlpatterns = [
    path("auth/otp/request/", OTPRequestView.as_view(), name="otp-request"),
    path("auth/otp/verify/", OTPVerifyView.as_view(), name="otp-verify"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/addresses/", AddressViewSetList.as_view(), name="address-list"),
    path("profile/addresses/<int:pk>/", AddressDetail.as_view(), name="address-detail"),
    # Admin
    path("admin/users/", AdminUserList.as_view(), name="admin-user-list"),
    path("admin/users/<int:pk>/", AdminUserDetail.as_view(), name="admin-user-detail"),
]
