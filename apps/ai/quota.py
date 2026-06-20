from django.utils import timezone

from apps.common.exceptions import BusinessError

from .models import AIUsageQuota

DEFAULT_TOKEN_LIMIT = 60000
DEFAULT_IMAGE_LIMIT = 10


def current_period():
    return timezone.now().strftime("%Y-%m")


def get_quota(user):
    """Return (creating if needed) the user's quota row for this month.

    Limits use the standard defaults (per-tariff AI limits were removed).
    """

    token_limit = DEFAULT_TOKEN_LIMIT
    image_limit = DEFAULT_IMAGE_LIMIT

    quota, created = AIUsageQuota.objects.get_or_create(
        user=user,
        period=current_period(),
        defaults={"token_limit": token_limit, "image_limit": image_limit},
    )
    if not created and (quota.token_limit != token_limit or quota.image_limit != image_limit):
        quota.token_limit = token_limit
        quota.image_limit = image_limit
        quota.save(update_fields=["token_limit", "image_limit", "updated_at"])
    return quota


def ensure_token_budget(user):
    quota = get_quota(user)
    if quota.tokens_used >= quota.token_limit:
        raise BusinessError("Oylik AI token kvotasi tugadi.")
    return quota


def ensure_image_budget(user):
    quota = get_quota(user)
    if quota.images_used >= quota.image_limit:
        raise BusinessError("Oylik AI rasm kvotasi tugadi.")
    return quota


def record_usage(quota, input_tokens=0, output_tokens=0, messages=0, images=0):
    quota.tokens_used += (input_tokens or 0) + (output_tokens or 0)
    quota.messages_used += messages
    quota.images_used += images
    quota.save(update_fields=["tokens_used", "messages_used", "images_used", "updated_at"])
