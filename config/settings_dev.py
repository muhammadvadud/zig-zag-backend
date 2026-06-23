"""Local dev settings for running the dashboard against sqlite without Redis.

Use: DJANGO_SETTINGS_MODULE=config.settings_dev POSTGRES_DB="" python manage.py runserver
"""

from .settings import *  # noqa: F401,F403

# No Redis in this environment -> in-memory cache (throttling / OTP still work).
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "zigzag-dev",
    }
}
