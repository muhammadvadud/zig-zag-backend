from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, phone, password, **extra):
        if not phone:
            raise ValueError("Telefon raqami majburiy.")
        user = self.model(phone=phone, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, phone, password=None, **extra):
        extra.setdefault("role", "customer")
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(phone, password, **extra)

    def create_superuser(self, phone, password=None, **extra):
        extra.update(role="admin", is_staff=True, is_superuser=True, is_phone_verified=True)
        return self._create(phone, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ("customer", "Customer"),
        ("employee", "Employee"),
        ("manager", "Manager"),
        ("admin", "Admin"),
    )
    LANG_CHOICES = (("uz", "uz"), ("ru", "ru"))

    phone = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(null=True, blank=True)
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, default="customer")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    language = models.CharField(max_length=2, choices=LANG_CHOICES, default="uz")
    # Telegram bot orqali xodim/menejer/adminga zakaz bildirishnomalarini yuborish uchun.
    telegram_chat_id = models.CharField(max_length=32, blank=True, default="")
    telegram_enabled = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.phone


class OTPCode(BaseModel):
    PURPOSE_CHOICES = (("login", "login"), ("register", "register"), ("reset", "reset"))

    phone = models.CharField(max_length=20, db_index=True)
    code_hash = models.CharField(max_length=128)
    purpose = models.CharField(max_length=16, choices=PURPOSE_CHOICES, default="login")
    attempts = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["phone", "purpose", "is_used"])]

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at


class Address(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    region = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    street = models.CharField(max_length=255)
    home = models.CharField(max_length=100)
    landmark = models.CharField(max_length=255, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.city}, {self.street}"
