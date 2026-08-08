"""
Trackside — ASGI application entry point.

Exposes the ASGI callable for async-capable servers.
Will be extended later for WebSocket support (real-time telemetry).
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_asgi_application()
