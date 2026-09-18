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


class DeviceCommand(models.Model):
    """
    A diagnostic or control command queued for an IoT device.
    """

    class CommandType(models.TextChoices):
        SELF_TEST = "self_test", "Self Test"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.CASCADE,
        related_name="commands",
        help_text="The device this command is for",
    )

    command_type = models.CharField(
        max_length=50,
        choices=CommandType.choices,
        help_text="Type of command to execute",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text="Execution status of the command",
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_device_commands",
        help_text="The Admin user who triggered this command",
    )

    requested_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the command was queued",
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the command was completed or failed",
    )

    result = models.JSONField(
        null=True,
        blank=True,
        help_text="Structured result payload from the device",
    )

    class Meta:
        db_table = "device_commands"
        ordering = ["-requested_at"]

    def __str__(self):
        return f"{self.command_type} for {self.device.id} ({self.status})"


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
