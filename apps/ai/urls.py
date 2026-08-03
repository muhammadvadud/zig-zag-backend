from django.urls import path

from . import views

urlpatterns = [
    # User-facing AI endpoints
    path("ai/conversations/", views.ConversationListCreate.as_view(), name="ai-conversations"),
    path("ai/conversations/<int:pk>/messages/", views.ConversationMessages.as_view(), name="ai-messages"),
    path("ai/usage/", views.AIUsageView.as_view(), name="ai-usage"),
    path("ai/images/", views.AIImageCreate.as_view(), name="ai-image-create"),
    path("ai/tryon/", views.AITryOnView.as_view(), name="ai-tryon"),
    path("ai/images/<str:public_id>/", views.AIImageDetail.as_view(), name="ai-image-detail"),
    # Existing admin endpoint
    path("admin/ai/usage/", views.AdminAIUsageList.as_view(), name="admin-ai-usage"),
    # Admin AI dashboard endpoints
    path("admin/ai/conversations/", views.AdminConversationListView.as_view(), name="admin-conversation-list"),
    path("admin/ai/conversations/<int:pk>/", views.AdminConversationDetailView.as_view(), name="admin-conversation-detail"),
    path("admin/ai/token-usage/", views.AdminTokenUsageListView.as_view(), name="admin-token-usage-list"),
    path("admin/ai/stats/", views.AdminAIStatsView.as_view(), name="admin-ai-stats"),
]
