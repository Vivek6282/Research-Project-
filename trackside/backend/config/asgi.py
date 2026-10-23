"""
Trackside — ASGI application entry point.

Exposes the ASGI callable for HTTP and WebSockets (real-time telemetry).
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddleware
from channels.sessions import CookieMiddleware, SessionMiddleware
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django_asgi_app = get_asgi_application()

import driving_sessions.routing
from config.area_session import AreaCookieMiddleware

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            # The same stack as AuthMiddlewareStack, with the role area's cookie picked from ?area= in between
            CookieMiddleware(
                AreaCookieMiddleware(
                    SessionMiddleware(
                        AuthMiddleware(URLRouter(driving_sessions.routing.websocket_urlpatterns))
                    )
                )
            )
        ),
    }
)
