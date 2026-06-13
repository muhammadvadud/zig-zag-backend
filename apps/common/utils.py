def get_client_ip(request):
    """Best-effort client IP, honouring a single reverse proxy."""

    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def current_language(request):
    """Resolve uz/ru from the Accept-Language header (defaults to uz)."""

    lang = (request.headers.get("Accept-Language") or "uz").lower()
    return "ru" if lang.startswith("ru") else "uz"
