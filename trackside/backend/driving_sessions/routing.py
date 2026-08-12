"""Trackside — Driving Sessions WebSocket routes."""

from django.urls import re_path
from driving_sessions.consumers import TelemetryConsumer

websocket_urlpatterns = [
    re_path(
        r"^ws/sessions/(?P<session_id>[0-9a-f-]+)/telemetry/$",
        TelemetryConsumer.as_asgi(),
    ),
]
