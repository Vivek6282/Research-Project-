"""
Trackside — ASGI application entry point.

Exposes the ASGI callable for HTTP and WebSockets (real-time telemetry).
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django_asgi_app = get_asgi_application()

import driving_sessions.routing

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(driving_sessions.routing.websocket_urlpatterns)
        ),
    }
)
