"""
Trackside — Devices Authentication.

Custom DRF authentication class for IoT device token authentication.
Reads 'Authorization: Device-Token <token>' or 'X-Device-Token: <token>' header,
authenticates the request as a DeviceUser, updates device.last_seen_at automatically,
and scopes data ingestion to the device's assigned user.
"""

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from devices.models import Device


class DeviceUser:
    """
    A lightweight proxy representing an authenticated IoT Device.
    Satisfies DRF request.user checks (is_authenticated=True, role="device").
    """
    is_authenticated = True
    is_anonymous = False
    is_staff = False
    is_superuser = False
    role = "device"

    def __init__(self, device: Device):
        self.device = device
        self.pk = device.pk
        self.id = device.id

    @property
    def assigned_to(self):
        return self.device.assigned_to

    def __str__(self):
        return f"DeviceUser({self.device.id})"


class DeviceTokenAuthentication(BaseAuthentication):
    """
    DRF Authentication class for physical IoT devices (ESP32).
    Header format:
      Authorization: Device-Token <raw_token>
    OR
      X-Device-Token: <raw_token>
    """

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        device_token_header = request.META.get("HTTP_X_DEVICE_TOKEN", "")

        raw_token = None

        if auth_header.startswith("Device-Token "):
            raw_token = auth_header[len("Device-Token "):].strip()
        elif auth_header.startswith("Bearer dt_") or auth_header.startswith("Token dt_"):
            raw_token = auth_header.split(" ", 1)[1].strip()
        elif device_token_header:
            raw_token = device_token_header.strip()

        if not raw_token:
            return None  # No device token provided; pass to next auth class

        token_hash = Device.hash_token(raw_token)
        device = Device.objects.filter(api_key_hash=token_hash).first()

        if not device or not device.verify_api_key(raw_token):
            raise exceptions.AuthenticationFailed("Invalid or inactive device token.")

        # Update last_seen_at and status automatically
        now = timezone.now()
        Device.objects.filter(pk=device.pk).update(
            last_seen_at=now,
            status=Device.Status.CONNECTED,
        )
        device.last_seen_at = now
        device.status = Device.Status.CONNECTED

        device_user = DeviceUser(device)
        return (device_user, device)
