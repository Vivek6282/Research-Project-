"""
Trackside — Security Tests for Device Token Scoping (S3) and Telemetry Input Validation (S4).

Tests:
S3 (Least privilege):
- Device token cannot access /api/sessions/ list (401/403)
- Device token cannot access /api/auth/users/ (accounts) (401/403)
- Device token cannot access /api/drivers/thresholds/ (drivers) (401/403)
- Device token cannot access /api/tracks/ (tracks) (401/403)

S4 (Telemetry input bounded & validated):
- Reject batch > 100 readings with 400
- Reject lateral_g < 0, > 10, NaN, inf
- Reject speed_kmh < 0, > 300, NaN, inf
- Reject gps_lat < -90, > 90, NaN, inf
- Reject gps_lng < -180, > 180, NaN, inf
- Reject lap_number < 1 or > 999
- Reject recorded_at > 5 minutes in future
- Reject posting to ended session with 409
- Throttle device_telemetry (ScopedRateThrottle)
"""

from datetime import timedelta
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

from tracks.models import Track
from devices.models import Device
from driving_sessions.models import Session

User = get_user_model()


class DeviceTokenLeastPrivilegeTestCase(TestCase):
    """S3: Device token works only on ingestion/device views, rejected elsewhere."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="s3_admin@test.local", name="Admin", role="admin", password="password123"
        )
        self.driver = User.objects.create_user(
            email="s3_driver@test.local", name="Driver", role="driver", password="password123"
        )
        self.track = Track.objects.create(name="S3 Track", created_by=self.admin)
        self.device = Device.objects.create(
            device_type=Device.DeviceType.GLOVE, assigned_to=self.driver
        )
        self.token = self.device.set_api_key()
        self.device.save()
        self.client.credentials(HTTP_AUTHORIZATION=f"Device-Token {self.token}")

    def test_device_token_rejected_on_sessions_list(self):
        """Device token gets 401/403 on /api/sessions/."""
        res = self.client.get("/api/sessions/")
        self.assertIn(res.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_device_token_rejected_on_accounts(self):
        """Device token gets 401/403 on /api/auth/users/."""
        res = self.client.get("/api/auth/users/")
        self.assertIn(res.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_device_token_rejected_on_drivers(self):
        """Device token gets 401/403 on /api/drivers/thresholds/."""
        res = self.client.get("/api/drivers/thresholds/")
        self.assertIn(res.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_device_token_rejected_on_tracks(self):
        """Device token gets 401/403 on /api/tracks/."""
        res = self.client.get("/api/tracks/")
        self.assertIn(res.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


class TelemetryInputValidationTestCase(TestCase):
    """S4: Telemetry input boundaries, types, session lifecycle, and throttling."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="s4_admin@test.local", name="Admin", role="admin", password="password123"
        )
        self.driver = User.objects.create_user(
            email="s4_driver@test.local", name="Driver", role="driver", password="password123"
        )
        self.track = Track.objects.create(name="S4 Track", created_by=self.admin)
        self.session = Session.objects.create(
            driver=self.driver, track=self.track, started_at=timezone.now()
        )
        self.device = Device.objects.create(
            device_type=Device.DeviceType.GLOVE, assigned_to=self.driver
        )
        self.token = self.device.set_api_key()
        self.device.save()
        self.client.credentials(HTTP_AUTHORIZATION=f"Device-Token {self.token}")

    def _valid_point(self, **overrides):
        point = {
            "recorded_at": timezone.now().isoformat(),
            "lateral_g": 1.1,
            "speed_kmh": 65.0,
            "gps_lat": 12.9716,
            "gps_lng": 77.5946,
            "lap_number": 1,
        }
        point.update(overrides)
        return point

    def test_reject_batch_larger_than_100(self):
        """Reject list longer than 100 readings with 400."""
        payload = [self._valid_point() for _ in range(101)]
        res = self.client.post(
            f"/api/sessions/{self.session.id}/telemetry/",
            payload,
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_invalid_lateral_g(self):
        """Reject lateral_g < 0, > 10, NaN, inf."""
        for bad_g in [-0.1, 10.1, "nan", "inf", "-inf"]:
            res = self.client.post(
                f"/api/sessions/{self.session.id}/telemetry/",
                self._valid_point(lateral_g=bad_g),
                format="json",
            )
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_invalid_speed_kmh(self):
        """Reject speed_kmh < 0, > 300, NaN, inf."""
        for bad_speed in [-1.0, 300.5, "nan", "inf"]:
            res = self.client.post(
                f"/api/sessions/{self.session.id}/telemetry/",
                self._valid_point(speed_kmh=bad_speed),
                format="json",
            )
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_invalid_gps_coordinates(self):
        """Reject latitude outside -90..90 and longitude outside -180..180 or NaN/inf."""
        for bad_lat in [-90.1, 90.1, "nan", "inf"]:
            res = self.client.post(
                f"/api/sessions/{self.session.id}/telemetry/",
                self._valid_point(gps_lat=bad_lat),
                format="json",
            )
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        for bad_lng in [-180.1, 180.1, "nan", "inf"]:
            res = self.client.post(
                f"/api/sessions/{self.session.id}/telemetry/",
                self._valid_point(gps_lng=bad_lng),
                format="json",
            )
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_invalid_lap_number(self):
        """Reject lap_number < 1 or > 999."""
        for bad_lap in [0, -1, 1000]:
            res = self.client.post(
                f"/api/sessions/{self.session.id}/telemetry/",
                self._valid_point(lap_number=bad_lap),
                format="json",
            )
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_recorded_at_too_far_in_future(self):
        """Reject recorded_at more than 5 minutes in the future."""
        future_time = timezone.now() + timedelta(minutes=6)
        res = self.client.post(
            f"/api/sessions/{self.session.id}/telemetry/",
            self._valid_point(recorded_at=future_time.isoformat()),
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_posting_to_ended_session(self):
        """Reject posting to a session that has ended_at set with 409 Conflict."""
        self.session.ended_at = timezone.now()
        self.session.save()

        res = self.client.post(
            f"/api/sessions/{self.session.id}/telemetry/",
            self._valid_point(),
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

    def test_device_telemetry_rate_throttle(self):
        """Verify device_telemetry throttle scope limits requests."""
        with override_settings(
            REST_FRAMEWORK={
                **{
                    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
                    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
                    "DEFAULT_THROTTLE_CLASSES": [],
                    "DEFAULT_THROTTLE_RATES": {
                        "device_telemetry": "2/min",
                        "login": "5/min",
                    },
                }
            }
        ):
            # First request: 201
            res1 = self.client.post(
                f"/api/sessions/{self.session.id}/telemetry/",
                self._valid_point(),
                format="json",
            )
            self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

            # Second request: 201
            res2 = self.client.post(
                f"/api/sessions/{self.session.id}/telemetry/",
                self._valid_point(),
                format="json",
            )
            self.assertEqual(res2.status_code, status.HTTP_201_CREATED)

            # Third request exceeds 2/min: 429
            res3 = self.client.post(
                f"/api/sessions/{self.session.id}/telemetry/",
                self._valid_point(),
                format="json",
            )
            self.assertEqual(res3.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
