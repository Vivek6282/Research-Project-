"""
Trackside — Driving Sessions WebSocket Consumers.

Provides real-time telemetry, alert, and biometric streaming to connected Coach and Driver dashboards.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer


class TelemetryConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for live session telemetry streaming.

    Route: ws://.../ws/sessions/<session_id>/telemetry/
    Pushes real-time telemetry points, lateral-g alerts, and biometric updates.
    """

    async def connect(self):
        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]
        self.room_group_name = f"session_{self.session_id}"

        # Join session group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave session group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name,
        )

    async def receive(self, text_data=None, bytes_data=None):
        """Handle incoming client ping/messages if needed."""
        if text_data:
            data = json.loads(text_data)
            if data.get("type") == "ping":
                await self.send(text_data=json.dumps({"type": "pong"}))

    # Event handlers for signals pushed to channel layer group
    async def telemetry_reading(self, event):
        """Send new telemetry reading to connected WebSocket client."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "telemetry_reading",
                    "data": event["data"],
                }
            )
        )

    async def alert_triggered(self, event):
        """Send new g-force/safety alert to connected WebSocket client."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "alert_triggered",
                    "data": event["data"],
                }
            )
        )

    async def biometric_reading(self, event):
        """Send new biometric reading to connected WebSocket client."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "biometric_reading",
                    "data": event["data"],
                }
            )
        )
