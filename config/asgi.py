"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()

async def application(scope, receive, send):
    if scope["type"] == "http":
        await django_asgi_app(scope, receive, send)
    elif scope["type"] == "websocket":
        # Frontend hali ham websocket ga ulanishga harakat qilyapti.
        # Xatolar (500) logni to'ldirib yubormasligi uchun jimgina yopamiz.
        await send({"type": "websocket.close"})
    else:
        raise NotImplementedError(f"Unknown scope type {scope['type']}")

