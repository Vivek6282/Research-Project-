"""
Trackside — Tests for who may read the device list and device detail (C9).

The device response includes assigned_to_name, so a driver must not be able to
list devices and see other drivers' names. Admin and Coach still can.
"""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from devices.models import Device

User = get_user_model()


class TestDeviceReadAccess(APITestCase):
    """Role checks for GET /api/devices/ and GET /api/devices/<id>/."""

    def setUp(self):
        """Create the users and data this test class needs."""
        super().setUp()
        make = User.objects.create_user
        self.admin = make(email="dr_admin@trackside.local", name="Admin", password="AdminPassword123!", role="admin")
        self.coach = make(email="dr_coach@trackside.local", name="Coach", password="CoachPassword123!", role="coach")
        self.driver_a = make(email="dr_a@trackside.local", name="Driver A", password="DriverPassword123!", role="driver")
        self.driver_b = make(email="dr_b@trackside.local", name="Driver B", password="DriverPassword123!", role="driver")
        self.glove_a = Device.objects.create(device_type=Device.DeviceType.GLOVE, assigned_to=self.driver_a)
        self.glove_b = Device.objects.create(device_type=Device.DeviceType.GLOVE, assigned_to=self.driver_b)

    def test_driver_gets_403_on_list_and_detail(self):
        """A driver cannot list devices or open any device, even their own."""
        self.client.force_authenticate(self.driver_a)
        self.assertEqual(self.client.get("/api/devices/").status_code, 403)
        self.assertEqual(self.client.get(f"/api/devices/{self.glove_b.id}/").status_code, 403)
        self.assertEqual(self.client.get(f"/api/devices/{self.glove_a.id}/").status_code, 403)

    def test_driver_response_never_contains_other_drivers_names(self):
        """The 403 body does not leak the names."""
        self.client.force_authenticate(self.driver_a)
        body = self.client.get("/api/devices/").content.decode()
        self.assertNotIn("Driver B", body)

    def test_admin_and_coach_can_still_read(self):
        """Admin and Coach see both devices with assigned_to_name."""
        for user in (self.admin, self.coach):
            self.client.force_authenticate(user)
            response = self.client.get("/api/devices/")
            self.assertEqual(response.status_code, 200)
            names = {row["assigned_to_name"] for row in response.data["results"]}
            self.assertEqual(names, {"Driver A", "Driver B"})
            self.assertEqual(self.client.get(f"/api/devices/{self.glove_a.id}/").status_code, 200)

    def test_anonymous_is_refused(self):
        """Logged-out callers get 401 or 403."""
        self.assertIn(self.client.get("/api/devices/").status_code, (401, 403))

    def test_writes_stay_admin_only(self):
        """Coach and driver still cannot change a device."""
        for user in (self.coach, self.driver_a):
            self.client.force_authenticate(user)
            response = self.client.patch(f"/api/devices/{self.glove_b.id}/", {"assigned_to": None}, format="json")
            self.assertEqual(response.status_code, 403)
