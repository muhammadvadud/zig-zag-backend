from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import StandardPagination

from .models import Notification
from .serializers import NotificationSerializer


class NotificationList(generics.ListAPIView):
    """Foydalanuvchining o'z bildirishnomalari — o'qilmaganlari birinchi."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).order_by(
            "is_read", "-created_at"
        )


class NotificationUnreadCount(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({"count": count})


class NotificationMarkRead(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = generics.get_object_or_404(
            Notification.objects.filter(recipient=request.user), pk=pk
        )
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read", "updated_at"])
        return Response(NotificationSerializer(notification).data)


class NotificationMarkAllRead(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = Notification.objects.filter(recipient=request.user, is_read=False).update(
            is_read=True
        )
        return Response({"updated": updated})



class TelegramToggle(APIView):
    """Xodim/menejer/admin o'z Telegram bildirishnomasini yoqadi/o'chiradi.

    Haqiqiy ulanish (chat_id) faqat Telegram bot orqali (/start + kontakt
    ulashish) o'rnatiladi — bu endpoint faqat allaqachon ulangan xodim uchun
    yoqish/o'chirish tumbleri (chat_id bo'lmasa yoqib bo'lmaydi)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.role not in ("employee", "manager", "admin"):
            return Response(
                {"error": {"code": "permission_denied", "message": "Faqat xodimlar uchun."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        enabled = bool(request.data.get("enabled", not user.telegram_enabled))
        if enabled and not user.telegram_chat_id:
            return Response(
                {
                    "error": {
                        "code": "telegram_not_linked",
                        "message": "Avval Telegram botga /start yozib, kontaktingizni ulashing.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.telegram_enabled = enabled
        user.save(update_fields=["telegram_enabled"])
        return Response({"telegram_enabled": user.telegram_enabled})
