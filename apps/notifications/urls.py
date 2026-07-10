from django.urls import path

from .views import (
    NotificationList,
    NotificationMarkAllRead,
    NotificationMarkRead,
    NotificationUnreadCount,
    TelegramToggle,
)

urlpatterns = [
    path("notifications/", NotificationList.as_view(), name="notification-list"),
    path("notifications/unread-count/", NotificationUnreadCount.as_view(), name="notification-unread-count"),
    path("notifications/read-all/", NotificationMarkAllRead.as_view(), name="notification-read-all"),
    path("notifications/<int:pk>/read/", NotificationMarkRead.as_view(), name="notification-read"),
    path("notifications/telegram/toggle/", TelegramToggle.as_view(), name="notification-telegram-toggle"),
]
