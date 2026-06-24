from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import Address, OTPCode, User


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    ordering = ("-date_joined",)
    list_display = ("phone", "full_name", "role", "is_phone_verified", "is_active")
    list_filter = ("role", "is_active", "is_phone_verified")
    search_fields = ("phone", "full_name", "email")
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Profil", {"fields": ("full_name", "email", "language")}),
        (
            "Ruxsatlar",
            {
                "fields": (
                    "role",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_phone_verified",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("phone", "password1", "password2", "role")}),
    )


@admin.register(Address)
class AddressAdmin(ModelAdmin):
    list_display = ("user", "city", "street", "is_default")
    search_fields = ("user__phone", "city", "street")
    list_filter = ("is_default", "region")


@admin.register(OTPCode)
class OTPCodeAdmin(ModelAdmin):
    list_display = ("phone", "purpose", "attempts", "is_used", "expires_at")
    list_filter = ("purpose", "is_used")
    search_fields = ("phone",)
