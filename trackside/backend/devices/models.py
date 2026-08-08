"""
Trackside — Devices app models.

Manages IoT device registration and connectivity status.
Devices include the glove unit, kart-mounted sensor unit, and biometric strap.
"""

import uuid
import secrets
import hashlib
import hmac
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

    api_key_hash = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text="SHA-256 hash of the device's secret API key token",
    )

    @staticmethod
    def hash_token(raw_token: str) -> str:
        if not raw_token:
            return ""
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    def set_api_key(self) -> str:
        """Generate a cryptographically secure raw token, save its SHA-256 hash, and return the raw token."""
        raw_token = f"dt_{secrets.token_urlsafe(32)}"
        self.api_key_hash = self.hash_token(raw_token)
        return raw_token

    def verify_api_key(self, raw_token: str) -> bool:
        """Constant-time comparison of raw token hash against stored hash."""
        if not self.api_key_hash or not raw_token:
            return False
        expected_hash = self.hash_token(raw_token)
        return hmac.compare_digest(self.api_key_hash, expected_hash)

    class Meta:
        db_table = "devices"
        ordering = ["device_type"]

    def __str__(self):
        assigned = self.assigned_to.name if self.assigned_to else "unassigned"
        return f"{self.get_device_type_display()} ({assigned}) — {self.status}"
