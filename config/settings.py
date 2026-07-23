"""
Django settings for the ZIG ZAG backend.

Configuration is driven by environment variables (see .env.example) so the same
image can run in development and production without code changes.
"""

from datetime import timedelta
from pathlib import Path

import environ
from django.templatetags.static import static  # noqa: F401  (available for UNFOLD)
from django.urls import reverse_lazy

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

# --------------------------------------------------------------------------- #
# Core
# --------------------------------------------------------------------------- #
SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-insecure-secret-key")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

INSTALLED_APPS = [
    # Model translation (must precede django.contrib.admin for admin integration)
    "modeltranslation",
    # Admin theme (must precede django.contrib.admin)
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    # Local
    "apps.common",
    "apps.accounts",
    "apps.catalog",
    "apps.services",
    "apps.cart",
    "apps.orders",
    "apps.payments",
    "apps.ai",
    "apps.notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise serves static files straight from Gunicorn (admin/Swagger CSS).
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.common.middleware.RequestIDMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

AUTH_USER_MODEL = "accounts.User"

# --------------------------------------------------------------------------- #
# Database
# --------------------------------------------------------------------------- #
if env("POSTGRES_DB", default=""):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB"),
            "USER": env("POSTGRES_USER"),
            "PASSWORD": env("POSTGRES_PASSWORD"),
            "HOST": env("POSTGRES_HOST", default="db"),
            "PORT": env("POSTGRES_PORT", default="5432"),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# --------------------------------------------------------------------------- #
# Cache / Redis
# --------------------------------------------------------------------------- #
REDIS_URL = env("REDIS_URL", default="redis://127.0.0.1:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

# --------------------------------------------------------------------------- #
# Celery
# --------------------------------------------------------------------------- #
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://127.0.0.1:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://127.0.0.1:6379/2")
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TIME_LIMIT = 300
CELERY_BEAT_SCHEDULE = {
    "cancel-unpaid-orders": {
        "task": "apps.orders.tasks.cancel_unpaid_orders",
        "schedule": 1800.0,  # har 30 daqiqada
    },
}

# --------------------------------------------------------------------------- #
# Password validation
# --------------------------------------------------------------------------- #
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

# --------------------------------------------------------------------------- #
# i18n
# --------------------------------------------------------------------------- #
LANGUAGE_CODE = "uz"
LANGUAGES = [("uz", "O'zbekcha"), ("ru", "Русский")]
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

# django-modeltranslation: uz is the default/fallback language.
MODELTRANSLATION_DEFAULT_LANGUAGE = "uz"
MODELTRANSLATION_LANGUAGES = ("uz", "ru")
MODELTRANSLATION_FALLBACK_LANGUAGES = ("uz",)

# --------------------------------------------------------------------------- #
# Static & media
# --------------------------------------------------------------------------- #
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# WhiteNoise compresses and serves static files; media goes to S3 or local disk.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

USE_S3 = env.bool("USE_S3", default=False)
if USE_S3:
    STORAGES["default"] = {"BACKEND": "storages.backends.s3.S3Storage"}
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default=None)
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default=None)
    AWS_QUERYSTRING_AUTH = False

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------------------- #
# REST framework
# --------------------------------------------------------------------------- #
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "300/min",
        "auth_otp": "5/hour",
        "ai_chat": "20/min",
        "ai_chat_day": "200/day",
        "ai_image": "10/day",
        "checkout": "10/min",
        "search": "30/min",
    },
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "apps.common.schema.TaggedAutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_MINUTES", default=15)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_DAYS", default=14)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "ZIG ZAG API",
    "DESCRIPTION": "Premium pardalar onlayn do'koni — backend API (AI integratsiyasi bilan).",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    # Section order and descriptions shown in Swagger.
    "TAGS": [
        {"name": "Auth", "description": "OTP orqali kirish, JWT token"},
        {"name": "Profil", "description": "Foydalanuvchi profili va manzillar"},
        {"name": "Katalog", "description": "Kategoriya, mahsulot, sharh, banner, FAQ"},
        {"name": "Sevimlilar", "description": "Wishlist"},
        {"name": "Tariflar", "description": "Smart / Lux / Premium xizmatlari"},
        {"name": "Savat", "description": "Savat va undagi elementlar"},
        {"name": "Buyurtmalar", "description": "Checkout, buyurtmalar, o'lchov so'rovi"},
        {"name": "To'lovlar", "description": "Payme va Click webhooklari"},
        {"name": "AI yordamchi", "description": "AI chat va kvota"},
        {"name": "AI rasm", "description": "Sun'iy rasm generatsiyasi"},
        {"name": "Admin", "description": "Boshqaruv (manager / admin)"},
        {"name": "Tizim", "description": "Health-check va xizmat endpointlari"},
    ],
    "SWAGGER_UI_SETTINGS": {
        "docExpansion": "none",
        "defaultModelsExpandDepth": -1,
        "filter": True,
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "tryItOutEnabled": True,
    },
}

# --------------------------------------------------------------------------- #
# Admin theme (django-unfold)
# --------------------------------------------------------------------------- #
def _nav_item(label, model, icon):
    return {"title": label, "icon": icon, "link": reverse_lazy(f"admin:{model}_changelist")}


UNFOLD = {
    "SITE_TITLE": "ZIG ZAG Admin",
    "SITE_HEADER": "ZIG ZAG",
    "SITE_SUBHEADER": "Premium pardalar — boshqaruv paneli",
    "SITE_SYMBOL": "storefront",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "SHOW_LANGUAGES": False,
    "COLORS": {
        "primary": {
            "50": "240 249 245",
            "100": "209 240 224",
            "200": "167 224 196",
            "300": "111 201 159",
            "400": "57 173 122",
            "500": "20 142 96",
            "600": "12 115 79",
            "700": "11 92 65",
            "800": "12 73 53",
            "900": "11 60 45",
            "950": "4 34 26",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Foydalanuvchilar",
                "separator": True,
                "items": [
                    _nav_item("Foydalanuvchilar", "accounts_user", "person"),
                    _nav_item("Manzillar", "accounts_address", "home_pin"),
                    _nav_item("OTP kodlar", "accounts_otpcode", "password"),
                ],
            },
            {
                "title": "Katalog",
                "separator": True,
                "items": [
                    _nav_item("Kategoriyalar", "catalog_category", "category"),
                    _nav_item("Uslublar", "catalog_style", "style"),
                    _nav_item("Xonalar", "catalog_room", "meeting_room"),
                    _nav_item("Chevarlar", "catalog_tailor", "content_cut"),
                    _nav_item("Mahsulotlar", "catalog_product", "inventory_2"),
                    _nav_item("Variantlar", "catalog_productvariant", "tune"),
                    _nav_item("Rasmlar", "catalog_productimage", "image"),
                    _nav_item("Ranglar", "catalog_color", "palette"),
                    _nav_item("Sharhlar", "catalog_review", "reviews"),
                    _nav_item("Sevimlilar", "catalog_favorite", "favorite"),
                    _nav_item("Kolleksiyalar", "catalog_collection", "collections"),
                    _nav_item("Bannerlar", "catalog_banner", "ad"),
                    _nav_item("Hero matnlari", "catalog_herocontent", "wallpaper"),
                    _nav_item("Ishlarimiz", "catalog_work", "photo_library"),
                    _nav_item("Mijozlar fikri", "catalog_testimonial", "format_quote"),
                    _nav_item("FAQ", "catalog_faq", "quiz"),
                ],
            },
            {
                "title": "Savdo",
                "separator": True,
                "items": [
                    _nav_item("Tariflar", "services_servicetariff", "sell"),
                    _nav_item("Savatlar", "cart_cart", "shopping_cart"),
                    _nav_item("Buyurtmalar", "orders_order", "receipt_long"),
                    _nav_item("O'lchov so'rovlari", "orders_measurementrequest", "straighten"),
                    _nav_item("Sovg'a kartalari", "orders_giftcard", "card_giftcard"),
                    _nav_item("To'lovlar", "payments_payment", "payments"),
                ],
            },
            {
                "title": "AI",
                "separator": True,
                "items": [
                    _nav_item("Suhbatlar", "ai_aiconversation", "forum"),
                    _nav_item("Rasm generatsiya", "ai_aiimagegeneration", "imagesmode"),
                    _nav_item("Kvota", "ai_aiusagequota", "data_usage"),
                ],
            },
            {
                "title": "Tizim",
                "separator": True,
                "items": [
                    _nav_item("Audit jurnali", "common_auditlog", "history"),
                    _nav_item("Bildirishnomalar", "notifications_notification", "notifications"),
                ],
            },
        ],
    },
}

# --------------------------------------------------------------------------- #
# CORS
# --------------------------------------------------------------------------- #
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True

# --------------------------------------------------------------------------- #
# OTP / SMS
# --------------------------------------------------------------------------- #
OTP_TTL_SECONDS = env.int("OTP_TTL_SECONDS", default=120)
OTP_MAX_ATTEMPTS = env.int("OTP_MAX_ATTEMPTS", default=5)
OTP_REQUEST_COOLDOWN = env.int("OTP_REQUEST_COOLDOWN", default=30)
OTP_DEBUG_RETURN_CODE = env.bool("OTP_DEBUG_RETURN_CODE", default=False)
SMS_PROVIDER = env("SMS_PROVIDER", default="")
SMS_API_KEY = env("SMS_API_KEY", default="")
SMS_SENDER = env("SMS_SENDER", default="")

# --------------------------------------------------------------------------- #
# Notifications (Telegram bot — xodim/menejer/admin bildirishnomalari)
# --------------------------------------------------------------------------- #
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default="")

# --------------------------------------------------------------------------- #
# AI
# --------------------------------------------------------------------------- #
AI_PROVIDER = env("AI_PROVIDER", default="anthropic")
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
AI_CHAT_MODEL = env("AI_CHAT_MODEL", default="claude-haiku-4-5-20251001")
AI_CHAT_MODEL_STRONG = env("AI_CHAT_MODEL_STRONG", default="claude-sonnet-4-6")
AI_MAX_OUTPUT_TOKENS = env.int("AI_MAX_OUTPUT_TOKENS", default=800)
AI_MAX_INPUT_CHARS = env.int("AI_MAX_INPUT_CHARS", default=2000)
AI_CONTEXT_WINDOW_MESSAGES = env.int("AI_CONTEXT_WINDOW_MESSAGES", default=10)
AI_STUB_MODE = env.bool("AI_STUB_MODE", default=not (bool(ANTHROPIC_API_KEY) or bool(OPENAI_API_KEY)))

# --------------------------------------------------------------------------- #
# Payments
# --------------------------------------------------------------------------- #
PAYME_MERCHANT_ID = env("PAYME_MERCHANT_ID", default="")
PAYME_KEY = env("PAYME_KEY", default="")
PAYME_ALLOWED_IPS = env.list("PAYME_ALLOWED_IPS", default=[])
CLICK_SERVICE_ID = env("CLICK_SERVICE_ID", default="")
CLICK_MERCHANT_ID = env("CLICK_MERCHANT_ID", default="")
CLICK_SECRET_KEY = env("CLICK_SECRET_KEY", default="")
CLICK_ALLOWED_IPS = env.list("CLICK_ALLOWED_IPS", default=[])

# --------------------------------------------------------------------------- #
# Security (tightened when DEBUG is off)
# --------------------------------------------------------------------------- #
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_REFERRER_POLICY = "same-origin"

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "apps.common.logging.JSONFormatter",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "json"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
    },
}

# --------------------------------------------------------------------------- #
# Sentry
# --------------------------------------------------------------------------- #
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )
