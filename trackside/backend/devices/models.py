"""
Trackside — Devices app models.

Manages IoT device registration and connectivity status.
Devices include the glove unit, kart-mounted sensor unit, and biometric strap.
"""

import uuid
from django.db import models
from django.conf import settings


class Device(models.Model):
    """
    An IoT device registered in the Trackside system.

    Tracks device type, assignment to a user, connection status,
    and last activity timestamp. Admin-managed.
    """

    class DeviceType(models.TextChoices):
        GLOVE = "glove", "Glove"
        KART_UNIT = "kart_unit", "Kart Unit"
        BIOMETRIC_STRAP = "biometric_strap", "Biometric Strap"

    class Status(models.TextChoices):
        CONNECTED = "connected", "Connected"
        PAIRING = "pairing", "Pairing"
        OFFLINE = "offline", "Offline"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    device_type = models.CharField(
        max_length=20,
        choices=DeviceType.choices,
        help_text="Type of IoT device",
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="devices",
        help_text="User this device is currently assigned to",
    )

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.OFFLINE,
        help_text="Current connection status of the device",
    )

    last_seen_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time the device sent data to the server",
    )

    class Meta:
        db_table = "devices"
        ordering = ["device_type"]

    def __str__(self):
        assigned = self.assigned_to.name if self.assigned_to else "unassigned"
        return f"{self.get_device_type_display()} ({assigned}) — {self.status}"
