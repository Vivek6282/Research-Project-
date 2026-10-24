"""
Trackside — Device events (Phase 2.0): things a device reports, not readings.

Crash suspected, lost contact, heartbeat, self-test result and "driver OK".
Each event carries an id made on the device, so a retried send is stored once.
Times: occurred_at is the device's clock, received_at is the server's clock and
is the one used for ordering; sequence is the device's own counter.
"""

import uuid

from django.conf import settings
from django.db import models


class DeviceEvent(models.Model):
    """One event reported by a device, or by a driver's phone page."""

    class EventType(models.TextChoices):
        CRASH_SUSPECTED = "crash_suspected", "Crash suspected"
        LOST_CONTACT = "lost_contact", "Lost contact"
        HEARTBEAT = "heartbeat", "Heartbeat"
        SELF_TEST_RESULT = "self_test_result", "Self-test result"
        DRIVER_OK = "driver_ok", "Driver OK"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.UUIDField(unique=True, help_text="Made on the device; a repeat of it is the same event")
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    device = models.ForeignKey("devices.Device", null=True, blank=True, on_delete=models.SET_NULL,
                               related_name="events", help_text="Sending device (device-token senders)")
    sent_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="device_events", help_text="Signed-in sender (a driver's phone page)")
    session = models.ForeignKey("driving_sessions.Session", null=True, blank=True, on_delete=models.CASCADE,
                                related_name="device_events")
    occurred_at = models.DateTimeField(help_text="When it happened, by the device's clock")
    sequence = models.PositiveBigIntegerField(help_text="The device's own counter, rising by one per message")
    received_at = models.DateTimeField(auto_now_add=True, help_text="When the server stored it (used for ordering)")
    payload = models.JSONField(default=dict, blank=True, help_text="Type-specific details, at most 8 KB")

    class Meta:
        ordering = ["received_at"]
        indexes = [models.Index(fields=["session", "received_at"]), models.Index(fields=["received_at"])]

    def sender_matches(self, device, user) -> bool:
        """True when this event was sent by the same device or the same signed-in user."""
        if device is not None:
            return self.device_id == device.id
        return user is not None and self.sent_by_id == user.id

    def __str__(self):
        return f"{self.event_type} {self.event_id}"
