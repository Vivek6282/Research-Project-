"""
Trackside — Unit tests for Audit Log Store & Diagnostics API.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from accounts.models import AuditLogEntry
from devices.models import Device

User = get_user_model()


@pytest.mark.django_db
class TestAuditLogAndDiagnostics:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()
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
        assert response.status_code == status.HTTP_201_CREATED

        audit_entry = AuditLogEntry.objects.filter(action=AuditLogEntry.Action.CREATE_USER).first()
        assert audit_entry is not None
        assert audit_entry.actor == self.admin
        assert audit_entry.target_user_name == "New Audit Driver"
        assert "Created DRIVER user" in audit_entry.details

    def test_user_deactivation_creates_audit_log(self):
        driver = User.objects.create_user(
            email="deact_target@trackside.local",
            name="Deact Target",
            role="driver",
            password="Password123!",
        )

        url = f"/api/auth/users/{driver.id}/"
        response = self.client.patch(url, {"is_active": False}, format="json")
        assert response.status_code == status.HTTP_200_OK

        audit_entry = AuditLogEntry.objects.filter(action=AuditLogEntry.Action.DEACTIVATE_USER).first()
        assert audit_entry is not None
        assert audit_entry.actor == self.admin
        assert audit_entry.target_user_name == "Deact Target"

    def test_audit_logs_list_endpoint(self):
        url = "/api/auth/audit-logs/"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "count_30_days" in data
        assert "results" in data

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
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["active_nodes"] == 1
        assert data["total_nodes"] == 2
        assert "db_query_time_ms" in data
        assert data["is_simulated_packet_data"] is True

        # Update offline device to connected -> verify active_nodes dynamically reflects real DB state
        dev2.status = Device.Status.CONNECTED
        dev2.save()

        response2 = self.client.get(url)
        assert response2.status_code == status.HTTP_200_OK
        data2 = response2.json()
        assert data2["active_nodes"] == 2
        assert data2["total_nodes"] == 2

