from django.urls import path

from .views import (
    AdminAIUsageList,
    AIImageCreate,
    AIImageDetail,
    AIUsageView,
    ConversationListCreate,
    ConversationMessages,
)

urlpatterns = [
    path("ai/conversations/", ConversationListCreate.as_view(), name="ai-conversations"),
    path("ai/conversations/<int:pk>/messages/", ConversationMessages.as_view(), name="ai-messages"),
    path("ai/usage/", AIUsageView.as_view(), name="ai-usage"),
    path("ai/images/", AIImageCreate.as_view(), name="ai-image-create"),
    path("ai/images/<str:public_id>/", AIImageDetail.as_view(), name="ai-image-detail"),
    path("admin/ai/usage/", AdminAIUsageList.as_view(), name="admin-ai-usage"),
]
