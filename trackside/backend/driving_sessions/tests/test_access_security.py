"""
Trackside — Security Tests for Session Access Scoping (S1).

Verifies strict deny-by-default access control:
- Unassigned devices cannot view any sessions (empty list or 404)
- Device A (assigned to Driver A) cannot view or modify Driver B's sessions
- Driver A cannot view or modify Driver B's sessions
- Endpoints verified:
    /api/sessions/
    /api/sessions/<id>/
    /api/sessions/<id>/telemetry/
    /api/sessions/<id>/alerts/
    /api/sessions/<id>/biometrics/
    /api/sessions/<id>/notes/
    /api/sessions/alerts/summary/
"""

import pytest
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

from accounts.models import User
from tracks.models import Track
from devices.models import Device
from driving_sessions.models import (
    Session, Telemetry, Alert, BiometricReading, SessionNote
)

User = get_user_model()


@pytest.mark.django_db
class SessionAccessSecurityTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Admin & Coach
        self.admin = User.objects.create_user(
            email="admin_s1@test.local", name="Admin", role="admin", password="password123"
        )
        self.coach = User.objects.create_user(
            email="coach_s1@test.local", name="Coach", role="coach", password="password123"
        )

        # Drivers
        self.driver_a = User.objects.create_user(
            email="driver_a@test.local", name="Driver A", role="driver", password="password123"
        )
        self.driver_b = User.objects.create_user(
            email="driver_b@test.local", name="Driver B", role="driver", password="password123"
        )

        # Track & Zone
        self.track = Track.objects.create(name="Track S1", created_by=self.admin)
        from tracks.models import Zone
        self.zone = Zone.objects.create(track=self.track, label="Hairpin", threshold_g=1.15)

        # Sessions
        self.session_a = Session.objects.create(
            driver=self.driver_a, track=self.track, started_at=timezone.now()
        )
        self.session_b = Session.objects.create(
            driver=self.driver_b, track=self.track, started_at=timezone.now()
        )

        # Telemetry, Alert, Biometric, Note for Session B
        self.telemetry_b = Telemetry.objects.create(
            session=self.session_b,
            zone=self.zone,
            recorded_at=timezone.now(),
            speed_kmh=60.0,
            lateral_g=1.1,
            gps_lat=12.9716,
            gps_lng=77.5946,
        )
        self.alert_b = Alert.objects.create(
            session=self.session_b,
            zone=self.zone,
            severity=Alert.Severity.RED,
            g_value=1.3,
            threshold_applied=1.15,
            triggered_at=timezone.now(),
        )
        self.bio_b = BiometricReading.objects.create(
            session=self.session_b,
            recorded_at=timezone.now(),
            heart_rate=140,
            spo2=98,
            breathing_rate=18,
        )
        self.note_b = SessionNote.objects.create(
            session=self.session_b, coach=self.coach, note_text="Driver B notes"
        )

        # Devices
        # Device A assigned to Driver A
        self.device_a = Device.objects.create(
            device_type=Device.DeviceType.GLOVE, assigned_to=self.driver_a
        )
        self.token_a = self.device_a.set_api_key()
        self.device_a.save()

        # Device B assigned to Driver B
        self.device_b = Device.objects.create(
            device_type=Device.DeviceType.GLOVE, assigned_to=self.driver_b
        )
        self.token_b = self.device_b.set_api_key()
        self.device_b.save()

        # Unassigned Device
        self.device_unassigned = Device.objects.create(
            device_type=Device.DeviceType.GLOVE, assigned_to=None
        )
        self.token_unassigned = self.device_unassigned.set_api_key()
        self.device_unassigned.save()

    def test_unassigned_device_cannot_read_any_session_endpoints(self):
        """Unassigned device gets empty list or 404 across all session endpoints."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Device-Token {self.token_unassigned}")

        # List sessions
        res = client.get("/api/sessions/")
        if res.status_code == status.HTTP_200_OK:
            self.assertEqual(len(res.data.get("results", res.data)), 0)
        else:
            self.assertIn(res.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

        # Detail session B
        res = client.get(f"/api/sessions/{self.session_b.id}/")
        self.assertIn(res.status_code, (status.HTTP_404_NOT_FOUND, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

        # Telemetry list session B
        res = client.get(f"/api/sessions/{self.session_b.id}/telemetry/")
        if res.status_code == status.HTTP_200_OK:
            self.assertEqual(len(res.data.get("results", res.data)), 0)
        else:
            self.assertIn(res.status_code, (status.HTTP_404_NOT_FOUND, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

        # Alerts list session B
        res = client.get(f"/api/sessions/{self.session_b.id}/alerts/")
        if res.status_code == status.HTTP_200_OK:
            self.assertEqual(len(res.data.get("results", res.data)), 0)
        else:
            self.assertIn(res.status_code, (status.HTTP_404_NOT_FOUND, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

        # Biometrics list session B
        res = client.get(f"/api/sessions/{self.session_b.id}/biometrics/")
        if res.status_code == status.HTTP_200_OK:
            self.assertEqual(len(res.data.get("results", res.data)), 0)
        else:
            self.assertIn(res.status_code, (status.HTTP_404_NOT_FOUND, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

        # Notes list session B
        res = client.get(f"/api/sessions/{self.session_b.id}/notes/")
        if res.status_code == status.HTTP_200_OK:
            self.assertEqual(len(res.data.get("results", res.data)), 0)
        else:
            self.assertIn(res.status_code, (status.HTTP_404_NOT_FOUND, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

        # Alert Summary
        res = client.get("/api/sessions/alerts/summary/")
        if res.status_code == status.HTTP_200_OK:
            self.assertEqual(res.data.get("total_sessions"), 0)
        else:
            self.assertIn(res.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_device_a_cannot_read_device_b_driver_sessions(self):
        """Device A cannot view or access Driver B's sessions."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Device-Token {self.token_a}")

        # List should not contain session B
        res = client.get("/api/sessions/")
        if res.status_code == status.HTTP_200_OK:
            session_ids = [s["id"] for s in res.data.get("results", res.data)]
            self.assertNotIn(str(self.session_b.id), session_ids)

        # Detail session B -> 404
        res = client.get(f"/api/sessions/{self.session_b.id}/")
        self.assertIn(res.status_code, (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED))

        # Telemetry session B -> empty or 404
        res = client.get(f"/api/sessions/{self.session_b.id}/telemetry/")
        if res.status_code == status.HTTP_200_OK:
            self.assertEqual(len(res.data.get("results", res.data)), 0)
        else:
            self.assertIn(res.status_code, (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN))

        # Ingestion to session B -> 403 Forbidden
        res = client.post(
            f"/api/sessions/{self.session_b.id}/telemetry/",
            {
                "recorded_at": timezone.now().isoformat(),
                "speed_kmh": 70.0,
                "lateral_g": 1.0,
            },
            format="json",
        )
        self.assertIn(res.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_driver_a_cannot_read_driver_b_data(self):
        """Driver A cannot read Driver B's session, telemetry, alerts, biometrics, notes, summary."""
        self.client.force_authenticate(user=self.driver_a)

        # List
        res = self.client.get("/api/sessions/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = [s["id"] for s in res.data.get("results", res.data)]
        self.assertNotIn(str(self.session_b.id), ids)

        # Detail
        res = self.client.get(f"/api/sessions/{self.session_b.id}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        # Telemetry list
        res = self.client.get(f"/api/sessions/{self.session_b.id}/telemetry/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data.get("results", res.data)), 0)

        # Alerts list
        res = self.client.get(f"/api/sessions/{self.session_b.id}/alerts/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data.get("results", res.data)), 0)

        # Biometrics list
        res = self.client.get(f"/api/sessions/{self.session_b.id}/biometrics/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data.get("results", res.data)), 0)

        # Notes list
        res = self.client.get(f"/api/sessions/{self.session_b.id}/notes/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data.get("results", res.data)), 0)

        # Alert Summary trying to view driver B
        res = self.client.get(f"/api/sessions/alerts/summary/?driver={self.driver_b.id}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Should return Driver A's data (or no sessions if none), NOT Driver B's sessions!
        if res.data.get("has_sessions"):
            self.assertEqual(res.data["latest_session"]["id"], str(self.session_a.id))
        else:
            self.assertEqual(res.data.get("total_sessions"), 0)
