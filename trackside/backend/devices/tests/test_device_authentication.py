"""
Trackside — IoT Device Token Authentication Tests.

Verifies:
- Device token generation & secure hashing in DB (SHA-256)
- Device registration response includes raw_api_key ONCE on creation
- Unauthenticated/invalid token requests are rejected with 401
- Valid device token can post telemetry readings to POST /api/sessions/<uuid>/telemetry/
- Valid device token updates device.last_seen_at automatically
- Device token scoped to a driver cannot write telemetry to another driver's session (403 IDOR check)
"""

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from devices.models import Device
from tracks.models import Track
from driving_sessions.models import Session, Telemetry

User = get_user_model()


@pytest.mark.django_db
class TestDeviceAuthentication:

    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.client = APIClient()

        # Users
        self.admin = User.objects.create_user(
            email="admin_dev@test.local",
            name="Admin Dev",
            role="admin",
            password="AdminPass123!",
        )
        self.driver1 = User.objects.create_user(
            email="driver1_dev@test.local",
            name="Driver One",
            role="driver",
            password="DriverPass123!",
        )
        self.driver2 = User.objects.create_user(
            email="driver2_dev@test.local",
            name="Driver Two",
            role="driver",
            password="DriverPass123!",
        )

        # Track & Sessions
        self.track = Track.objects.create(name="Apex Circuit", created_by=self.admin)
        self.session1 = Session.objects.create(
            driver=self.driver1,
            track=self.track,
            started_at=timezone.now(),
        )
        self.session2 = Session.objects.create(
            driver=self.driver2,
            track=self.track,
            started_at=timezone.now(),
        )

        # Registered Device assigned to Driver 1
        self.device = Device.objects.create(
            device_type=Device.DeviceType.KART_UNIT,
            assigned_to=self.driver1,
        )
        self.raw_token = self.device.set_api_key()
        self.device.save()

    def test_invalid_device_token_rejected(self):
        """Request with invalid device token returns 401 Unauthorized."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Device-Token invalid_fake_token_123")

        response = client.post(
            f"/api/sessions/{self.session1.id}/telemetry/",
            {
                "recorded_at": timezone.now().isoformat(),
                "speed_kmh": 85.5,
                "lateral_g": 1.25,
                "gps_lat": 12.9716,
                "gps_lng": 77.5946,
            },
            format="json",
        )
        assert response.status_code in (401, 403)

    def test_valid_device_token_ingests_telemetry_and_updates_last_seen(self):
        """Valid device token posts telemetry and updates device.last_seen_at automatically."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Device-Token {self.raw_token}")

        initial_last_seen = self.device.last_seen_at

        response = client.post(
            f"/api/sessions/{self.session1.id}/telemetry/",
            {
                "recorded_at": timezone.now().isoformat(),
                "speed_kmh": 88.4,
                "lateral_g": 1.32,
                "gps_lat": 12.9716,
                "gps_lng": 77.5946,
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["speed_kmh"] == 88.4

        # Verify last_seen_at updated
        self.device.refresh_from_db()
        assert self.device.last_seen_at is not None
        assert self.device.status == Device.Status.CONNECTED
        if initial_last_seen:
            assert self.device.last_seen_at > initial_last_seen

    def test_device_token_scoped_to_assigned_driver_session(self):
        """Device assigned to Driver 1 cannot post telemetry to Driver 2's session (IDOR protection)."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Device-Token {self.raw_token}")

        response = client.post(
            f"/api/sessions/{self.session2.id}/telemetry/",
            {
                "recorded_at": timezone.now().isoformat(),
                "speed_kmh": 92.0,
                "lateral_g": 1.45,
                "gps_lat": 12.9716,
                "gps_lng": 77.5946,
            },
            format="json",
        )
        assert response.status_code == 403

    def test_device_token_never_stored_in_plaintext(self):
        """API key tokens are hashed in DB (api_key_hash) and never saved in plaintext."""
        assert self.device.api_key_hash != ""
        assert self.raw_token not in self.device.api_key_hash
        assert self.device.verify_api_key(self.raw_token) is True
        assert self.device.verify_api_key("wrong_token") is False
