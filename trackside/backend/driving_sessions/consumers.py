"""
Trackside — Driving Sessions WebSocket Consumers.

Provides real-time telemetry, alert, and biometric streaming to connected Coach and Driver dashboards.
"""

import json

from django.core.serializers.json import DjangoJSONEncoder
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from driving_sessions.access import can_access_session


class TelemetryConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for live session telemetry streaming.

    Route: ws://.../ws/sessions/<session_id>/telemetry/
    Pushes real-time telemetry points, lateral-g alerts, and biometric updates.
    """

    async def connect(self):
        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]
        self.room_group_name = f"session_{self.session_id}"

        # S2: Reject unauthenticated users (close code 4401)
        user = self.scope.get("user")
        if not user or not getattr(user, "is_authenticated", False):
            await self.close(code=4401)
            return

        # S2: Reject unauthorized users based on session ownership (close code 4403)
        has_access = await database_sync_to_async(can_access_session)(user, self.session_id)
        if not has_access:
            await self.close(code=4403)
            return

        # Join session group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave session group
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name,
            )

    async def receive(self, text_data=None, bytes_data=None):
        """Handle incoming client ping/messages safely."""
        # S2: Ignore messages over 1 KB
        if text_data:
            if len(text_data.encode("utf-8")) > 1024:
                return
            # Catch bad JSON without crashing
            try:
                data = json.loads(text_data)
            except Exception:
                return

            # Only answer ping
            if isinstance(data, dict) and data.get("type") == "ping":
                await self.send(text_data=json.dumps({"type": "pong"}))
        elif bytes_data:
            if len(bytes_data) > 1024:
                return

    # Event handlers for signals pushed to channel layer group
    async def telemetry_reading(self, event):
        """Send new telemetry reading to connected WebSocket client."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "telemetry_reading",
                    "data": event["data"],
                },
                cls=DjangoJSONEncoder,
            )
        )

    async def alert_triggered(self, event):
        """Send new g-force/safety alert to connected WebSocket client."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "alert_triggered",
                    "data": event["data"],
                },
                cls=DjangoJSONEncoder,
            )
        )

    async def biometric_reading(self, event):
        """Send new biometric reading to connected WebSocket client."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "biometric_reading",
                    "data": event["data"],
                },
                cls=DjangoJSONEncoder,
            )
        )
