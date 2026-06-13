import logging
import secrets

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

from .models import OTPCode

logger = logging.getLogger(__name__)


def _cooldown_key(phone):
    return f"otp:cooldown:{phone}"


def can_request_otp(phone):
    """Enforce a per-phone cooldown between OTP requests."""

    return not cache.get(_cooldown_key(phone))


def generate_otp(phone, purpose):
    """Create a hashed OTP, store it and return the plain code (for sending)."""

    code = f"{secrets.randbelow(1000000):06d}"
    OTPCode.objects.create(
        phone=phone,
        code_hash=make_password(code),
        purpose=purpose,
        expires_at=timezone.now() + timedelta(seconds=settings.OTP_TTL_SECONDS),
    )
    cache.set(_cooldown_key(phone), 1, timeout=settings.OTP_REQUEST_COOLDOWN)
    send_sms(phone, code)
    return code


def verify_otp(phone, code, purpose):
    """Return True if the code matches an active OTP, else False.

    Increments the attempt counter and burns the OTP on success.
    """

    otp = (
        OTPCode.objects.filter(phone=phone, purpose=purpose, is_used=False)
        .order_by("-created_at")
        .first()
    )
    if not otp or otp.is_expired:
        return False
    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        return False

    if check_password(code, otp.code_hash):
        otp.is_used = True
        otp.save(update_fields=["is_used", "updated_at"])
        return True

    otp.attempts += 1
    otp.save(update_fields=["attempts", "updated_at"])
    return False


def send_sms(phone, code):
    """Deliver the OTP. Without a configured provider we log to the console."""

    text = f"ZIG ZAG tasdiqlash kodi: {code}"
    if not settings.SMS_PROVIDER:
        logger.info("SMS (console) -> %s: %s", phone, text)
        return
    # Real provider integrations (eskiz / playmobile) wire in here.
    logger.info("SMS via %s -> %s", settings.SMS_PROVIDER, phone)
