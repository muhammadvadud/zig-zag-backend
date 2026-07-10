from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ("created_at", "recipient", "kind", "title", "is_read", "order")
    list_filter = ("kind", "is_read")
    search_fields = ("title", "body", "recipient__phone", "recipient__full_name")
    readonly_fields = [f.name for f in Notification._meta.fields]

    def has_add_permission(self, request):
        return False
