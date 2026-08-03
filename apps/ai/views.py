import os
import uuid

from django.core.files.storage import default_storage
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsStaffRole
from apps.common.throttles import (
    AIChatDailyThrottle,
    AIChatThrottle,
    AIImageThrottle,
)

from .models import AIConversation, AIImageGeneration, AIUsageQuota
from .quota import get_quota
from .serializers import (
    AdminAIUsageSerializer,
    AdminConversationDetailSerializer,
    AdminConversationListSerializer,
    AdminTokenUsageDetailSerializer,
    AIConversationSerializer,
    AIImageGenerationSerializer,
    AIMessageSerializer,
    ImageCreateSerializer,
    MessageCreateSerializer,
    TryOnSerializer,
)
from .service import handle_user_message
from .tasks import generate_ai_image


def _owner_filter(request):
    """Scope conversations to the authenticated caller."""

    return {"user": request.user}


class ConversationListCreate(generics.ListCreateAPIView):
    serializer_class = AIConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AIConversation.objects.filter(**_owner_filter(self.request))

    def perform_create(self, serializer):
        serializer.save(**_owner_filter(self.request))


class ConversationMessages(APIView):
    permission_classes = [IsAuthenticated]

    def get_throttles(self):
        if self.request.method == "POST":
            return [AIChatThrottle(), AIChatDailyThrottle()]
        return super().get_throttles()

    def _get_conversation(self, request, pk):
        try:
            return AIConversation.objects.get(pk=pk, **_owner_filter(request))
        except AIConversation.DoesNotExist:
            raise PermissionDenied("Bu suhbat sizga tegishli emas.")

    def get(self, request, pk):
        conversation = self._get_conversation(request, pk)
        messages = conversation.messages.all()
        return Response(AIMessageSerializer(messages, many=True).data)

    def post(self, request, pk):
        conversation = self._get_conversation(request, pk)
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assistant, suggestions, quota = handle_user_message(
            conversation, request.user, serializer.validated_data["content"]
        )

        return Response(
            {
                "message_id": assistant.id,
                "role": "assistant",
                "content": assistant.content,
                "suggested_products": suggestions,
            }
        )


class AIUsageView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        quota = get_quota(request.user)
        return Response(
            {
                "period": quota.period,
                "tokens_used": quota.tokens_used,
                "token_limit": quota.token_limit,
                "images_used": quota.images_used,
                "image_limit": quota.image_limit,
                "messages_used": quota.messages_used,
            }
        )


class AIImageCreate(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [AIImageThrottle]

    def post(self, request):
        user = request.user

        # Idempotency: a repeated request with the same key returns the first job.
        idem = request.headers.get("Idempotency-Key", "")
        if idem:
            existing = AIImageGeneration.objects.filter(
                user=user, idempotency_key=idem
            ).first()
            if existing:
                return Response(
                    {"id": existing.public_id, "status": existing.status},
                    status=status.HTTP_202_ACCEPTED,
                )

        from .quota import ensure_image_budget

        ensure_image_budget(user)

        serializer = ImageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        gen = AIImageGeneration.objects.create(
            user=user,
            source_image=data.get("source_image"),
            product_id=data.get("product_id"),
            prompt=data.get("prompt", ""),
            idempotency_key=idem,
        )
        generate_ai_image.delay(gen.id)
        return Response(
            {"id": gen.public_id, "status": gen.status}, status=status.HTTP_202_ACCEPTED
        )


class AIImageDetail(generics.RetrieveAPIView):
    serializer_class = AIImageGenerationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "public_id"
    lookup_url_kwarg = "public_id"

    def get_queryset(self):
        return AIImageGeneration.objects.filter(user=self.request.user)


class AITryOnView(APIView):
    """Foydalanuvchi xona rasmini yuboradi, pardali natija rasmini oladi.

    AI_STUB_MODE yoqilgan (real provider/internet yo'q) — shuning uchun stub
    yo'l yuklangan rasmni media/tryon/ ga saqlaydi va uning absolute URL'ini
    "natija" sifatida qaytaradi. Frontend oqimi shu bilan to'liq ishlaydi.
    """

    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [AIImageThrottle]

    def post(self, request):
        serializer = TryOnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image = serializer.validated_data["image"]

        # Yuklangan xona rasmini media/tryon/ ga saqlaymiz (placeholder natija).
        _, ext = os.path.splitext(image.name)
        ext = ext.lower() if ext else ".jpg"
        name = default_storage.get_available_name(f"tryon/{uuid.uuid4().hex}{ext}")
        saved_path = default_storage.save(name, image)
        url = default_storage.url(saved_path)
        absolute_url = request.build_absolute_uri(url)

        return Response({"image": absolute_url}, status=status.HTTP_200_OK)


class AdminAIUsageList(generics.ListAPIView):
    """Staff view of AI spend per user (tokens, images, messages)."""

    serializer_class = AdminAIUsageSerializer
    permission_classes = [IsStaffRole]
    queryset = AIUsageQuota.objects.select_related("user").all()
    filterset_fields = ["period"]
    search_fields = ["user__phone"]
    ordering_fields = ["tokens_used", "images_used"]
    ordering = ["-tokens_used"]


# ─── Admin dashboard views ───────────────────────────────────────────────────

from django.db.models import Count, Sum  # noqa: E402


class AdminConversationListView(generics.ListAPIView):
    """List all conversations across all users for admin."""

    serializer_class = AdminConversationListSerializer
    permission_classes = [IsStaffRole]
    search_fields = ["title", "user__phone", "user__full_name"]
    filterset_fields = ["user__id"]

    def get_queryset(self):
        return (
            AIConversation.objects.select_related("user")
            .annotate(
                message_count=Count("messages"),
                total_tokens=(
                    Sum("messages__input_tokens", default=0)
                    + Sum("messages__output_tokens", default=0)
                ),
            )
            .order_by("-updated_at")
        )


class AdminConversationDetailView(generics.RetrieveAPIView):
    """Retrieve a conversation with all messages for admin."""

    serializer_class = AdminConversationDetailSerializer
    permission_classes = [IsStaffRole]
    queryset = AIConversation.objects.select_related("user").prefetch_related("messages")


class AdminTokenUsageListView(generics.ListAPIView):
    """List token usage across all users for admin."""

    serializer_class = AdminTokenUsageDetailSerializer
    permission_classes = [IsStaffRole]
    search_fields = ["user__phone", "user__full_name"]
    filterset_fields = ["period"]

    def get_queryset(self):
        return AIUsageQuota.objects.select_related("user").order_by("-tokens_used")


class AdminAIStatsView(APIView):
    """Aggregate AI usage stats for admin dashboard."""

    permission_classes = [IsStaffRole]

    def get(self, request):
        from .models import AIMessage

        # Total stats
        total_conversations = AIConversation.objects.count()
        total_messages = AIMessage.objects.count()
        total_images = AIImageGeneration.objects.count()

        # Active users (users with at least one conversation)
        active_users = AIConversation.objects.values("user").distinct().count()

        # Token aggregates
        token_agg = AIUsageQuota.objects.aggregate(
            total_tokens=Sum("tokens_used"),
        )
        total_tokens = token_agg["total_tokens"] or 0

        # Top users by token usage
        top_users_qs = (
            AIUsageQuota.objects.select_related("user")
            .order_by("-tokens_used")
            .values(
                "user__id",
                "user__phone",
                "user__full_name",
                "tokens_used",
                "token_limit",
                "images_used",
                "messages_used",
                "period",
            )[:10]
        )

        top_users = []
        for u in top_users_qs:
            tokens_val = u["tokens_used"] or 0
            limit = u["token_limit"] or 500000
            top_users.append(
                {
                    "user_id": u["user__id"],
                    "phone": u["user__phone"],
                    "full_name": u["user__full_name"],
                    "tokens_used": tokens_val,
                    "token_limit": limit,
                    "images_used": u["images_used"] or 0,
                    "messages_used": u["messages_used"] or 0,
                    "usage_percent": round((tokens_val / limit) * 100, 1) if limit else 0,
                    "period": u["period"],
                }
            )

        return Response(
            {
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "total_images": total_images,
                "total_tokens": total_tokens,
                "active_users": active_users,
                "top_users": top_users,
            }
        )
