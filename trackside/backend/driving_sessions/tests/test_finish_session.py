"""
Trackside — Tests for Session Finish Endpoint (Prompt 6, F3).
Verifies:
- Finish sets ended_at when called by an authorized device token
- Second call is idempotent (returns 200 without changing ended_at)
- Best lap computation includes the final lap once ended_at is set
- Ingesting telemetry after finish returns 409 Conflict
- Denied access for: other driver's device, unassigned device, driver, and anonymous
- Allowed access for: Admin and Coach
"""

import uuid
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from tracks.models import Track, Zone
from devices.models import Device
from driving_sessions.models import Session, Telemetry
from driving_sessions.serializers import SessionSerializer

User = get_user_model()


class TestSessionFinishEndpoint(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Users
        self.admin = User.objects.create_user(
            email="admin_fin@trackside.local", name="Admin", role="admin", password="password123"
        )
        self.coach = User.objects.create_user(
            email="coach_fin@trackside.local", name="Coach", role="coach", password="password123"
        )
        self.driver_a = User.objects.create_user(
            email="driver_a_fin@trackside.local", name="Driver A", role="driver", password="password123"
        )
        self.driver_b = User.objects.create_user(
            email="driver_b_fin@trackside.local", name="Driver B", role="driver", password="password123"
        )

        # Track & Zone
        self.track = Track.objects.create(name="Finish Circuit", created_by=self.admin)
        self.zone = Zone.objects.create(track=self.track, label="Hairpin", threshold_g=1.15)

        # Sessions
        self.session_a = Session.objects.create(
            driver=self.driver_a,
            track=self.track,
            mode=Session.Mode.SAFETY,
            started_at=timezone.now() - timedelta(minutes=10),
            ended_at=None,
        )

        # Devices
        # Device A -> Driver A
        self.device_a = Device.objects.create(
            device_type=Device.DeviceType.GLOVE, assigned_to=self.driver_a
        )
        self.token_a = self.device_a.set_api_key()
        self.device_a.save()

        # Device B -> Driver B
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

    def test_finish_sets_ended_at_by_assigned_device(self):
        """Device token assigned to driver sets ended_at on the driver's session."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Device-Token {self.token_a}")
        res = self.client.post(f"/api/sessions/{self.session_a.id}/finish/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.session_a.refresh_from_db()
        self.assertIsNotNone(self.session_a.ended_at)
        self.assertIsNotNone(res.data.get("ended_at"))

    def test_finish_second_call_keeps_same_time(self):
        """Second finish call returns 200 without changing ended_at timestamp."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Device-Token {self.token_a}")
        res1 = self.client.post(f"/api/sessions/{self.session_a.id}/finish/")
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.session_a.refresh_from_db()
        first_ended_at = self.session_a.ended_at

        res2 = self.client.post(f"/api/sessions/{self.session_a.id}/finish/")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.session_a.refresh_from_db()
        self.assertEqual(self.session_a.ended_at, first_ended_at)

    def test_finish_does_not_overwrite_preset_ended_at(self):
        """Pre-set ended_at is preserved atomically and not overwritten by finish."""
        preset_time = timezone.now() - timedelta(hours=1)
        self.session_a.ended_at = preset_time
        self.session_a.save(update_fields=["ended_at"])

        self.client.credentials(HTTP_AUTHORIZATION=f"Device-Token {self.token_a}")
        res = self.client.post(f"/api/sessions/{self.session_a.id}/finish/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.session_a.refresh_from_db()
        self.assertEqual(self.session_a.ended_at, preset_time)

    def test_best_lap_now_includes_last_lap_after_finish(self):
        """When ended_at is set by finish, the last in-progress lap is included in best lap."""
        base_time = timezone.now() - timedelta(minutes=5)

        # Lap 1: 60 seconds (5 readings)
        for i in range(5):
            Telemetry.objects.create(
                session=self.session_a,
                recorded_at=base_time + timedelta(seconds=i * 15),
                lateral_g=0.8,
                speed_kmh=50.0,
                gps_lat=12.97,
                gps_lng=77.59,
                lap_number=1,
            )

        # Lap 2 (faster): 40 seconds (5 readings)
        lap2_start = base_time + timedelta(seconds=70)
        for i in range(5):
            Telemetry.objects.create(
                session=self.session_a,
                recorded_at=lap2_start + timedelta(seconds=i * 10),
                lateral_g=1.0,
                speed_kmh=65.0,
                gps_lat=12.97,
                gps_lng=77.59,
                lap_number=2,
            )

        # Before finish: Lap 2 is ignored as in-progress (ended_at is None)
        # Lap 1 is completed (lap 1 < max_lap 2) and has duration 60s
        data_before = SessionSerializer(self.session_a).data
        self.assertIsNotNone(data_before["best_lap"])
        self.assertEqual(data_before["best_lap"], "1:00.000")

        # Finish session via device token
        self.client.credentials(HTTP_AUTHORIZATION=f"Device-Token {self.token_a}")
        res = self.client.post(f"/api/sessions/{self.session_a.id}/finish/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # After finish: Lap 2 is now completed (ended_at is set) and becomes best lap (40s < 60s)
        self.session_a.refresh_from_db()
        data_after = SessionSerializer(self.session_a).data
        self.assertIsNotNone(data_after["best_lap"])
        self.assertEqual(data_after["best_lap"], "0:40.000")

    def test_telemetry_after_finish_gets_409(self):
        """Ingesting telemetry into an ended session returns 409 Conflict."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Device-Token {self.token_a}")
        res = self.client.post(f"/api/sessions/{self.session_a.id}/finish/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        telemetry_payload = {
            "lateral_g": 0.85,
            "speed_kmh": 55.0,
            "recorded_at": timezone.now().isoformat(),
            "lap_number": 3,
        }
        tel_res = self.client.post(
            f"/api/sessions/{self.session_a.id}/telemetry/",
            data=telemetry_payload,
            format="json",
        )
        self.assertEqual(tel_res.status_code, status.HTTP_409_CONFLICT)

    def test_other_driver_device_denied(self):
        """Device B assigned to Driver B gets 404 when attempting to finish Driver A's session."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Device-Token {self.token_b}")
        res = self.client.post(f"/api/sessions/{self.session_a.id}/finish/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.data, {"error": "Session not found."})

    def test_unassigned_device_denied(self):
        """Unassigned device gets 404 when attempting to finish any session."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Device-Token {self.token_unassigned}")
        res = self.client.post(f"/api/sessions/{self.session_a.id}/finish/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.data, {"error": "Session not found."})

    def test_inaccessible_and_nonexistent_sessions_return_identical_404(self):
        """Nonexistent session ID and forbidden session ID return identical 404 status and body."""
        nonexistent_id = uuid.uuid4()

        # Nonexistent session request with Device A
        self.client.credentials(HTTP_AUTHORIZATION=f"Device-Token {self.token_a}")
        res_nonexistent = self.client.post(f"/api/sessions/{nonexistent_id}/finish/")
        self.assertEqual(res_nonexistent.status_code, status.HTTP_404_NOT_FOUND)

        # Inaccessible session request with Device B on Session A
        self.client.credentials(HTTP_AUTHORIZATION=f"Device-Token {self.token_b}")
        res_forbidden = self.client.post(f"/api/sessions/{self.session_a.id}/finish/")
        self.assertEqual(res_forbidden.status_code, status.HTTP_404_NOT_FOUND)

        # Inaccessible session request with unassigned device on Session A
        self.client.credentials(HTTP_AUTHORIZATION=f"Device-Token {self.token_unassigned}")
        res_unassigned = self.client.post(f"/api/sessions/{self.session_a.id}/finish/")
        self.assertEqual(res_unassigned.status_code, status.HTTP_404_NOT_FOUND)

        # Status and body must be strictly identical across all 404 cases
        self.assertEqual(res_nonexistent.data, res_forbidden.data)
        self.assertEqual(res_nonexistent.data, res_unassigned.data)
        self.assertEqual(res_forbidden.data, {"error": "Session not found."})

    def test_driver_denied_from_finishing_session(self):
        """Driver is denied from directly calling finish endpoint."""
        self.client.force_authenticate(user=self.driver_a)
        res = self.client.post(f"/api/sessions/{self.session_a.id}/finish/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_denied(self):
        """Anonymous request is rejected with 403 Forbidden by SessionAuthentication."""
        res = self.client.post(f"/api/sessions/{self.session_a.id}/finish/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_and_coach_allowed(self):
        """Admin and Coach can finish sessions."""
        # Coach
        self.client.force_authenticate(user=self.coach)
        res = self.client.post(f"/api/sessions/{self.session_a.id}/finish/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Admin on a new session
        new_session = Session.objects.create(
            driver=self.driver_b, track=self.track, started_at=timezone.now()
        )
        self.client.force_authenticate(user=self.admin)
        res_admin = self.client.post(f"/api/sessions/{new_session.id}/finish/")
        self.assertEqual(res_admin.status_code, status.HTTP_200_OK)
        new_session.refresh_from_db()
        self.assertIsNotNone(new_session.ended_at)
