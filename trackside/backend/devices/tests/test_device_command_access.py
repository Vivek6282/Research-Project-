"""
Trackside — Only the device itself may use the device command endpoints (P3).

GET /api/devices/me/commands/pending/ and POST /api/devices/me/commands/<id>/complete/
belong to the device. A signed-in person used to cause a server error there; now they get 403.
"""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from devices.models import Device, DeviceCommand

User = get_user_model()


class TestDeviceCommandAccess(APITestCase):
    """Role checks and input checks for the device command endpoints."""

    def setUp(self):
        """Create people of every role, a device with a token, and one pending command."""
        super().setUp()
        make = User.objects.create_user
        self.people = {role: make(email=f"dc_{role}@trackside.local", name=role, password="Password123!", role=role)
                       for role in ("admin", "coach", "driver")}
        self.device = Device.objects.create(device_type="glove", assigned_to=self.people["driver"])
        self.token = self.device.set_api_key()
        self.device.save()
        self.command = DeviceCommand.objects.create(device=self.device, command_type="self_test")
        self.pending = "/api/devices/me/commands/pending/"
        self.complete = f"/api/devices/me/commands/{self.command.id}/complete/"

    def device_headers(self):
        """The header a device sends."""
        return {"HTTP_AUTHORIZATION": f"Device-Token {self.token}"}

    def test_people_of_every_role_get_403_not_a_server_error(self):
        """Admin, coach and driver are refused on both endpoints and the command is untouched."""
        for person in self.people.values():
            self.client.force_authenticate(person)
            self.assertEqual(self.client.get(self.pending).status_code, 403, person.role)
            self.assertEqual(self.client.post(self.complete, {"status": "completed"}, format="json").status_code, 403, person.role)
            self.assertEqual(self.client.patch(self.complete, {"status": "completed"}, format="json").status_code, 403, person.role)
        self.command.refresh_from_db()
        self.assertEqual(self.command.status, DeviceCommand.Status.PENDING)

    def test_anonymous_is_refused(self):
        """No credentials, no access."""
        self.assertIn(self.client.get(self.pending).status_code, (401, 403))
        self.assertIn(self.client.post(self.complete, {}, format="json").status_code, (401, 403))

    def test_the_device_itself_can_read_and_complete_its_command(self):
        """With its token the device sees the pending command and can complete it."""
        response = self.client.get(self.pending, **self.device_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        done = self.client.post(self.complete, {"status": "completed", "result": {"ok": True}}, format="json", **self.device_headers())
        self.assertEqual(done.status_code, 200, done.data)
        self.command.refresh_from_db()
        self.assertEqual((self.command.status, self.command.result), ("completed", {"ok": True}))

    def test_a_device_cannot_set_an_invalid_status_or_touch_another_devices_command(self):
        """Only completed/failed are accepted; another device's command is a 404."""
        bad = self.client.post(self.complete, {"status": "pending"}, format="json", **self.device_headers())
        self.assertEqual(bad.status_code, 400)
        other = Device.objects.create(device_type="glove")
        theirs = DeviceCommand.objects.create(device=other, command_type="self_test")
        response = self.client.post(f"/api/devices/me/commands/{theirs.id}/complete/", {"status": "completed"}, format="json", **self.device_headers())
        self.assertEqual(response.status_code, 404)
        theirs.refresh_from_db()
        self.assertEqual(theirs.status, DeviceCommand.Status.PENDING)
