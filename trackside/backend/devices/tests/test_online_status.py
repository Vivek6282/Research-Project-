"""
Trackside — Unit tests for Device Honest Online Status & Window (D3).

Tests:
- Online window: seen 29s ago is online, 31s ago is offline (frozen time).
- Throttling: last_seen_at is not rewritten within 5 seconds.
- API exposure: is_online and last_seen_at exposed in Device API.
- Data migration: rows with status='connected' convert to 'offline'.
- Device token request does not set status to connected.
"""

from datetime import timedelta
from unittest.mock import patch
from django.utils import timezone
from django.contrib.auth import get_user_model
import importlib
from rest_framework import status
from rest_framework.test import APITestCase
from devices.models import Device

migration_0004 = importlib.import_module("devices.migrations.0004_status_connected_to_offline")
set_connected_to_offline = migration_0004.set_connected_to_offline

User = get_user_model()


class DeviceOnlineStatusTestCase(APITestCase):
    """
    Test suite verifying honest online status calculation and contact throttling.
    """

    def setUp(self):
        """
        Create test admin, driver, and device with API key.
        """
        self.admin = User.objects.create_superuser(
            email="admin_online@test.local",
            name="Admin Online",
            password="AdminPassword123!",
        )
        self.driver = User.objects.create_user(
            email="driver_online@test.local",
            name="Driver Online",
            role="driver",
            password="DriverPassword123!",
        )
        self.device = Device.objects.create(
            device_type=Device.DeviceType.GLOVE,
            assigned_to=self.driver,
            status=Device.Status.OFFLINE,
        )
        self.raw_token = self.device.set_api_key()
        self.device.save()

    def test_online_window_freeze_time(self):
        """
        Freeze time: seen 29 seconds ago is online, 31 seconds ago is offline.
        """
        frozen_time = timezone.now()

        with patch("django.utils.timezone.now", return_value=frozen_time):
            # Device seen 29 seconds ago (inside default 30s window)
            self.device.last_seen_at = frozen_time - timedelta(seconds=29)
            self.device.save()
            self.assertTrue(self.device.is_online)

            # Device seen 31 seconds ago (outside default 30s window)
            self.device.last_seen_at = frozen_time - timedelta(seconds=31)
            self.device.save()
            self.assertFalse(self.device.is_online)

            # Device never seen
            self.device.last_seen_at = None
            self.device.save()
            self.assertFalse(self.device.is_online)

    def test_last_seen_at_not_rewritten_within_5s(self):
        """
        last_seen_at is throttled and not rewritten in DB if contacted within 5 seconds.
        """
        t0 = timezone.now()
        with patch("django.utils.timezone.now", return_value=t0):
            self.client.credentials(HTTP_AUTHORIZATION=f"Device-Token {self.raw_token}")
            res = self.client.get("/api/devices/me/commands/pending/")
            self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.device.refresh_from_db()
        first_seen = self.device.last_seen_at
        self.assertIsNotNone(first_seen)

        # Contact 3 seconds later -> must NOT rewrite last_seen_at
        t1 = t0 + timedelta(seconds=3)
        with patch("django.utils.timezone.now", return_value=t1):
            res2 = self.client.get("/api/devices/me/commands/pending/")
            self.assertEqual(res2.status_code, status.HTTP_200_OK)

        self.device.refresh_from_db()
        self.assertEqual(self.device.last_seen_at, first_seen)

        # Contact 6 seconds later -> must update last_seen_at
        t2 = t0 + timedelta(seconds=6)
        with patch("django.utils.timezone.now", return_value=t2):
            res3 = self.client.get("/api/devices/me/commands/pending/")
            self.assertEqual(res3.status_code, status.HTTP_200_OK)

        self.device.refresh_from_db()
        self.assertGreater(self.device.last_seen_at, first_seen)

    def test_device_api_exposes_is_online_and_last_seen_at(self):
        """
        Device API endpoint exposes computed is_online and last_seen_at timestamps.
        """
        now = timezone.now()
        self.device.last_seen_at = now
        self.device.save()

        self.client.force_authenticate(user=self.admin)
        url = f"/api/devices/{self.device.id}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("is_online", response.data)
        self.assertIn("last_seen_at", response.data)
        self.assertTrue(response.data["is_online"])
        self.assertIsNotNone(response.data["last_seen_at"])

    def test_status_not_set_to_connected_on_request(self):
        """
        Device authentication updates last_seen_at but does not set status to connected.
        """
        self.device.status = Device.Status.OFFLINE
        self.device.save()

        self.client.credentials(HTTP_AUTHORIZATION=f"Device-Token {self.raw_token}")
        response = self.client.get("/api/devices/me/commands/pending/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.device.refresh_from_db()
        self.assertNotEqual(self.device.status, "connected")
        self.assertEqual(self.device.status, Device.Status.OFFLINE)
        self.assertTrue(self.device.is_online)

    def test_data_migration_connected_to_offline(self):
        """
        Data migration sets any existing connected rows to offline without data loss.
        """
        # Create a mock apps registry for the migration function
        from django.apps import apps
        # Force a device row to have 'connected' status via raw query / direct update
        Device.objects.filter(pk=self.device.pk).update(status="connected")
        self.device.refresh_from_db()
        self.assertEqual(self.device.status, "connected")

        set_connected_to_offline(apps, None)

        self.device.refresh_from_db()
        self.assertEqual(self.device.status, "offline")
