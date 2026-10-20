"""
Trackside — Unit tests for Admin Device Assignment & Validation (D1).

Tests:
- Admin can assign a device to an active driver.
- Non-admin (coach, driver) cannot PATCH device (403 Forbidden).
- Rejection of invalid assignments (coach, admin, deactivated driver, unknown ID).
- Unassigning a device by setting assigned_to to null.
- One-per-type rule: driver can only hold one device per type; reassignment atomically unassigns the old device.
- A driver can hold different device types simultaneously.
- Past driving sessions are never modified by a device reassignment.
"""

import uuid
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from devices.models import Device
from tracks.models import Track
from driving_sessions.models import Session

User = get_user_model()


class DeviceAssignmentAPITestCase(APITestCase):
    """
    Test suite for Admin device assignment endpoints and validation rules.
    """

    def setUp(self):
        """
        Set up test users, devices, and baseline track.
        """
        self.admin = User.objects.create_superuser(
            email="admin_dev@test.local",
            name="Admin Dev",
            password="AdminPass123!",
        )
        self.coach = User.objects.create_user(
            email="coach_dev@test.local",
            name="Coach Dev",
            role="coach",
            password="CoachPass123!",
        )
        self.driver_a = User.objects.create_user(
            email="driver_a@test.local",
            name="Driver A",
            role="driver",
            password="DriverPass123!",
        )
        self.driver_b = User.objects.create_user(
            email="driver_b@test.local",
            name="Driver B",
            role="driver",
            password="DriverPass123!",
        )
        self.inactive_driver = User.objects.create_user(
            email="inactive_drv@test.local",
            name="Inactive Driver",
            role="driver",
            is_active=False,
            password="DriverPass123!",
        )

        self.glove_1 = Device.objects.create(
            device_type=Device.DeviceType.GLOVE,
            assigned_to=self.driver_a,
        )
        self.glove_2 = Device.objects.create(
            device_type=Device.DeviceType.GLOVE,
            assigned_to=None,
        )
        self.kart_unit = Device.objects.create(
            device_type=Device.DeviceType.KART_UNIT,
            assigned_to=None,
        )

    def test_admin_assign_device_to_active_driver(self):
        """
        Admin assigns an unassigned device to an active driver successfully.
        """
        self.client.force_authenticate(user=self.admin)
        url = f"/api/devices/{self.glove_2.id}/"
        response = self.client.patch(url, {"assigned_to": str(self.driver_b.id)}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.glove_2.refresh_from_db()
        self.assertEqual(self.glove_2.assigned_to, self.driver_b)
        self.assertEqual(response.data["assigned_to_name"], "Driver B")

    def test_non_admin_cannot_patch_device(self):
        """
        Non-admin users receive 403 Forbidden when trying to PATCH a device.
        """
        self.client.force_authenticate(user=self.coach)
        url = f"/api/devices/{self.glove_2.id}/"
        response = self.client.patch(url, {"assigned_to": str(self.driver_b.id)}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.driver_a)
        response2 = self.client.patch(url, {"assigned_to": str(self.driver_a.id)}, format="json")
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)

    def test_assign_rejects_coach(self):
        """
        Attempting to assign a device to a coach returns 400 Bad Request.
        """
        self.client.force_authenticate(user=self.admin)
        url = f"/api/devices/{self.glove_2.id}/"
        response = self.client.patch(url, {"assigned_to": str(self.coach.id)}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("assigned_to", response.data)

    def test_assign_rejects_admin(self):
        """
        Attempting to assign a device to an admin returns 400 Bad Request.
        """
        self.client.force_authenticate(user=self.admin)
        url = f"/api/devices/{self.glove_2.id}/"
        response = self.client.patch(url, {"assigned_to": str(self.admin.id)}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("assigned_to", response.data)

    def test_assign_rejects_deactivated_driver(self):
        """
        Attempting to assign a device to a deactivated driver returns 400 Bad Request.
        """
        self.client.force_authenticate(user=self.admin)
        url = f"/api/devices/{self.glove_2.id}/"
        response = self.client.patch(url, {"assigned_to": str(self.inactive_driver.id)}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("assigned_to", response.data)

    def test_assign_rejects_unknown_id(self):
        """
        Attempting to assign a device to an unknown user ID returns 400 Bad Request.
        """
        self.client.force_authenticate(user=self.admin)
        url = f"/api/devices/{self.glove_2.id}/"
        unknown_id = str(uuid.uuid4())
        response = self.client.patch(url, {"assigned_to": unknown_id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("assigned_to", response.data)

    def test_admin_unassign_device(self):
        """
        Admin sets assigned_to to null to unassign a device.
        """
        self.client.force_authenticate(user=self.admin)
        url = f"/api/devices/{self.glove_1.id}/"
        response = self.client.patch(url, {"assigned_to": None}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.glove_1.refresh_from_db()
        self.assertIsNone(self.glove_1.assigned_to)

    def test_one_per_type_rule_moves_device(self):
        """
        Assigning a second glove to Driver A unassigns the old glove in the same transaction.
        """
        self.client.force_authenticate(user=self.admin)
        # Driver A already has glove_1. Assign glove_2 to Driver A.
        url = f"/api/devices/{self.glove_2.id}/"
        response = self.client.patch(url, {"assigned_to": str(self.driver_a.id)}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.glove_2.refresh_from_db()
        self.glove_1.refresh_from_db()

        # Glove 2 is now assigned to Driver A
        self.assertEqual(self.glove_2.assigned_to, self.driver_a)
        # Old glove 1 is unassigned
        self.assertIsNone(self.glove_1.assigned_to)
        # Reassignment notice is present
        self.assertIn("reassignment_notice", response.data)
        self.assertIn("Glove was moved from Driver A", response.data["reassignment_notice"])

    def test_one_per_type_allows_different_types(self):
        """
        A driver can hold one glove and one kart unit at the same time without conflict.
        """
        self.client.force_authenticate(user=self.admin)
        url = f"/api/devices/{self.kart_unit.id}/"
        response = self.client.patch(url, {"assigned_to": str(self.driver_a.id)}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.glove_1.refresh_from_db()
        self.kart_unit.refresh_from_db()

        self.assertEqual(self.glove_1.assigned_to, self.driver_a)
        self.assertEqual(self.kart_unit.assigned_to, self.driver_a)

    def test_past_sessions_unaffected_by_reassignment(self):
        """
        Past driving sessions remain attached to their driver after device reassignment.
        """
        track = Track.objects.create(name="Reassign Test Track", created_by=self.admin)
        session = Session.objects.create(
            driver=self.driver_a,
            track=track,
            started_at=timezone.now(),
        )

        self.client.force_authenticate(user=self.admin)
        url = f"/api/devices/{self.glove_1.id}/"
        response = self.client.patch(url, {"assigned_to": str(self.driver_b.id)}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        session.refresh_from_db()
        self.assertEqual(session.driver, self.driver_a)

    def test_reassigned_device_token_security_s1(self):
        # Security S1: device token permissions immediately shift to new driver after reassignment.
        track = Track.objects.create(name="Security Track", created_by=self.admin)
        session_a = Session.objects.create(driver=self.driver_a, track=track, started_at=timezone.now())
        session_b = Session.objects.create(driver=self.driver_b, track=track, started_at=timezone.now())

        glove_token = self.glove_1.set_api_key()
        self.glove_1.save()

        # Glove 1 starts assigned to Driver A: can ingest and read session A, denied on session B
        self.client.credentials(HTTP_AUTHORIZATION=f"Device-Token {glove_token}")
        payload = {"speed_kmh": 65.0, "lateral_g": 1.1, "recorded_at": timezone.now().isoformat(), "gps_lat": 11.01, "gps_lng": 76.95}
        self.assertEqual(self.client.post(f"/api/sessions/{session_a.id}/telemetry/", payload, format="json").status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.client.post(f"/api/sessions/{session_b.id}/telemetry/", payload, format="json").status_code, status.HTTP_403_FORBIDDEN)

        res_a1 = self.client.get(f"/api/sessions/{session_a.id}/telemetry/")
        self.assertEqual(len(res_a1.data.get("results", res_a1.data)), 1)
        res_b1 = self.client.get(f"/api/sessions/{session_b.id}/telemetry/")
        self.assertEqual(len(res_b1.data.get("results", res_b1.data)), 0)

        # Admin moves Glove 1 to Driver B
        self.client.credentials()
        self.client.force_authenticate(user=self.admin)
        patch_res = self.client.patch(f"/api/devices/{self.glove_1.id}/", {"assigned_to": str(self.driver_b.id)}, format="json")
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)

        # Glove 1 token can now read and write Driver B's session and CANNOT Driver A's
        self.client.force_authenticate(user=None)
        self.client.credentials(HTTP_AUTHORIZATION=f"Device-Token {glove_token}")
        self.assertEqual(self.client.post(f"/api/sessions/{session_a.id}/telemetry/", payload, format="json").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.post(f"/api/sessions/{session_b.id}/telemetry/", payload, format="json").status_code, status.HTTP_201_CREATED)

        res_a2 = self.client.get(f"/api/sessions/{session_a.id}/telemetry/")
        self.assertEqual(len(res_a2.data.get("results", res_a2.data)), 0)
        res_b2 = self.client.get(f"/api/sessions/{session_b.id}/telemetry/")
        self.assertEqual(len(res_b2.data.get("results", res_b2.data)), 1)
