"""
Trackside — Driving Sessions Django Signals.

Broadcasts newly created telemetry, alert, and biometric records to connected
WebSocket clients via Django Channels group layer.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from driving_sessions.models import Telemetry, Alert, BiometricReading
from driving_sessions.serializers import (
    TelemetrySerializer,
    AlertSerializer,
    BiometricReadingSerializer,
)


@receiver(post_save, sender=Telemetry)
def broadcast_telemetry(sender, instance, created, **kwargs):
    """Broadcast new telemetry reading to session WebSocket group."""
    if created and instance.session_id:
        channel_layer = get_channel_layer()
        if channel_layer:
            data = TelemetrySerializer(instance).data
            async_to_sync(channel_layer.group_send)(
                f"session_{instance.session_id}",
                {
                    "type": "telemetry_reading",
                    "data": data,
                },
            )


@receiver(post_save, sender=Alert)
def broadcast_alert(sender, instance, created, **kwargs):
    """Broadcast new alert to session WebSocket group."""
    if created and instance.session_id:
        channel_layer = get_channel_layer()
        if channel_layer:
            data = AlertSerializer(instance).data
            async_to_sync(channel_layer.group_send)(
                f"session_{instance.session_id}",
                {
                    "type": "alert_triggered",
                    "data": data,
                },
            )


@receiver(post_save, sender=BiometricReading)
def broadcast_biometric(sender, instance, created, **kwargs):
    """Broadcast new biometric reading to session WebSocket group."""
    if created and instance.session_id:
        channel_layer = get_channel_layer()
        if channel_layer:
            data = BiometricReadingSerializer(instance).data
            async_to_sync(channel_layer.group_send)(
                f"session_{instance.session_id}",
                {
                    "type": "biometric_reading",
                    "data": data,
                },
            )
