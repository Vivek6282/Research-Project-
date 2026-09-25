from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from devices.models import Device, DeviceCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class DeviceCommandsAPITestCase(APITestCase):

    def setUp(self):
        self.admin_user = User.objects.create_user(
            email="admin@test.com", password="pwd", name="Admin", role="admin"
        )
        self.driver_user = User.objects.create_user(
            email="driver@test.com", password="pwd", name="Driver", role="driver"
        )
        self.test_device = Device.objects.create(device_type=Device.DeviceType.GLOVE)
        self.device_token = self.test_device.set_api_key()
        self.test_device.save()

    def test_admin_can_trigger_command(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("device-commands", kwargs={"pk": self.test_device.pk})
        response = self.client.post(url, {"command_type": DeviceCommand.CommandType.SELF_TEST})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DeviceCommand.objects.count(), 1)
        self.assertEqual(DeviceCommand.objects.first().requested_by, self.admin_user)

    def test_non_admin_cannot_trigger_command(self):
        self.client.force_authenticate(user=self.driver_user)
        url = reverse("device-commands", kwargs={"pk": self.test_device.pk})
        response = self.client.post(url, {"command_type": DeviceCommand.CommandType.SELF_TEST})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(DeviceCommand.objects.count(), 0)

    def test_device_can_fetch_pending_commands(self):
        DeviceCommand.objects.create(
            device=self.test_device,
            command_type=DeviceCommand.CommandType.SELF_TEST,
            requested_by=self.admin_user,
        )

        url = reverse("device-commands-pending")
        self.client.credentials(HTTP_AUTHORIZATION=f"Device-Token {self.device_token}")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["command_type"], "self_test")

    def test_device_can_complete_own_command(self):
        cmd = DeviceCommand.objects.create(
            device=self.test_device,
            command_type=DeviceCommand.CommandType.SELF_TEST,
            requested_by=self.admin_user,
        )

        url = reverse("device-commands-complete", kwargs={"pk": cmd.pk})
        self.client.credentials(HTTP_AUTHORIZATION=f"Device-Token {self.device_token}")
        response = self.client.post(
            url,
            {
                "status": DeviceCommand.Status.COMPLETED,
                "result": {"boot": True, "ping_latency_ms": 15},
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cmd.refresh_from_db()
        self.assertEqual(cmd.status, DeviceCommand.Status.COMPLETED)
        self.assertTrue(cmd.result["boot"])
        self.assertIsNotNone(cmd.completed_at)

    def test_device_cannot_complete_other_device_command(self):
        other_device = Device.objects.create(device_type=Device.DeviceType.KART_UNIT)
        cmd = DeviceCommand.objects.create(
            device=other_device,
            command_type=DeviceCommand.CommandType.SELF_TEST,
            requested_by=self.admin_user,
        )

        url = reverse("device-commands-complete", kwargs={"pk": cmd.pk})
        self.client.credentials(HTTP_AUTHORIZATION=f"Device-Token {self.device_token}")
        response = self.client.post(
            url,
            {
                "status": DeviceCommand.Status.COMPLETED,
                "result": {"boot": True},
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
