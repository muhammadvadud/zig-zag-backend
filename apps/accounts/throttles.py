from rest_framework.throttling import SimpleRateThrottle


class OTPRequestThrottle(SimpleRateThrottle):
    """Rate-limit OTP requests by phone number (and fall back to IP)."""

    scope = "auth_otp"

    def get_cache_key(self, request, view):
        phone = request.data.get("phone") if hasattr(request, "data") else None
        ident = phone or self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}
