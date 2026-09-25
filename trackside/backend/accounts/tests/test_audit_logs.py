"""
Trackside — Unit tests for Audit Log Store & Diagnostics API.
"""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from accounts.models import AuditLogEntry
from devices.models import Device

User = get_user_model()


class TestAuditLogAndDiagnostics(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="admin_audit_test@trackside.local",
            name="Audit Test Admin",
            password="AdminPassword123!",
        )
        self.client.force_authenticate(user=self.admin)

    def test_user_creation_creates_audit_log(self):
        url = "/api/auth/users/"
        payload = {
            "name": "New Audit Driver",
            "role": "driver",
            "password": "Password123!",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        audit_entry = AuditLogEntry.objects.filter(action=AuditLogEntry.Action.CREATE_USER).first()
        self.assertIsNotNone(audit_entry)
        self.assertEqual(audit_entry.actor, self.admin)
        self.assertEqual(audit_entry.target_user_name, "New Audit Driver")
        self.assertIn("Created DRIVER user", audit_entry.details)

    def test_user_deactivation_creates_audit_log(self):
        driver = User.objects.create_user(
            email="deact_target@trackside.local",
            name="Deact Target",
            role="driver",
            password="Password123!",
        )

        url = f"/api/auth/users/{driver.id}/"
        response = self.client.patch(url, {"is_active": False}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        audit_entry = AuditLogEntry.objects.filter(action=AuditLogEntry.Action.DEACTIVATE_USER).first()
        self.assertIsNotNone(audit_entry)
        self.assertEqual(audit_entry.actor, self.admin)
        self.assertEqual(audit_entry.target_user_name, "Deact Target")

    def test_audit_logs_list_endpoint(self):
        url = "/api/auth/audit-logs/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("count_30_days", data)
        self.assertIn("results", data)

    def test_diagnostics_endpoint(self):
        # Create sample devices
        dev1 = Device.objects.create(
            device_type=Device.DeviceType.GLOVE,
            status=Device.Status.CONNECTED,
        )
        dev2 = Device.objects.create(
            device_type=Device.DeviceType.KART_UNIT,
            status=Device.Status.OFFLINE,
        )

        url = "/api/auth/diagnostics/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["active_nodes"], 1)
        self.assertEqual(data["total_nodes"], 2)
        self.assertIn("db_query_time_ms", data)
        self.assertTrue(data["is_simulated_packet_data"])

        # Update offline device to connected -> verify active_nodes dynamically reflects real DB state
        dev2.status = Device.Status.CONNECTED
        dev2.save()

        response2 = self.client.get(url)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        data2 = response2.json()
        self.assertEqual(data2["active_nodes"], 2)
        self.assertEqual(data2["total_nodes"], 2)
