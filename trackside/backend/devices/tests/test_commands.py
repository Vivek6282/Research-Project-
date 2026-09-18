import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from devices.models import Device, DeviceCommand
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def admin_user():
    return User.objects.create_user(email="admin@test.com", password="pwd", name="Admin", role="admin")

@pytest.fixture
def driver_user():
    return User.objects.create_user(email="driver@test.com", password="pwd", name="Driver", role="driver")

@pytest.fixture
def test_device():
    device = Device.objects.create(device_type=Device.DeviceType.GLOVE)
    return device

@pytest.fixture
def device_token(test_device):
    token = test_device.set_api_key()
    test_device.save()
    return token

@pytest.mark.django_db
def test_admin_can_trigger_command(api_client, admin_user, test_device):
    api_client.force_authenticate(user=admin_user)
    url = reverse("device-commands", kwargs={"pk": test_device.pk})
    response = api_client.post(url, {"command_type": DeviceCommand.CommandType.SELF_TEST})
    
    assert response.status_code == status.HTTP_201_CREATED
    assert DeviceCommand.objects.count() == 1
    assert DeviceCommand.objects.first().requested_by == admin_user

@pytest.mark.django_db
def test_non_admin_cannot_trigger_command(api_client, driver_user, test_device):
    api_client.force_authenticate(user=driver_user)
    url = reverse("device-commands", kwargs={"pk": test_device.pk})
    response = api_client.post(url, {"command_type": DeviceCommand.CommandType.SELF_TEST})
    
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert DeviceCommand.objects.count() == 0

@pytest.mark.django_db
def test_device_can_fetch_pending_commands(api_client, test_device, device_token, admin_user):
    DeviceCommand.objects.create(
        device=test_device,
        command_type=DeviceCommand.CommandType.SELF_TEST,
        requested_by=admin_user
    )
    
    url = reverse("device-commands-pending")
    api_client.credentials(HTTP_AUTHORIZATION=f"Device-Token {device_token}")
    response = api_client.get(url)
    
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["command_type"] == "self_test"

@pytest.mark.django_db
def test_device_can_complete_own_command(api_client, test_device, device_token, admin_user):
    cmd = DeviceCommand.objects.create(
        device=test_device,
        command_type=DeviceCommand.CommandType.SELF_TEST,
        requested_by=admin_user
    )
    
    url = reverse("device-commands-complete", kwargs={"pk": cmd.pk})
    api_client.credentials(HTTP_AUTHORIZATION=f"Device-Token {device_token}")
    response = api_client.post(url, {
        "status": DeviceCommand.Status.COMPLETED,
        "result": {"boot": True, "ping_latency_ms": 15}
    }, format='json')
    
    assert response.status_code == status.HTTP_200_OK
    cmd.refresh_from_db()
    assert cmd.status == DeviceCommand.Status.COMPLETED
    assert cmd.result["boot"] is True
    assert cmd.completed_at is not None

@pytest.mark.django_db
def test_device_cannot_complete_other_device_command(api_client, test_device, device_token, admin_user):
    other_device = Device.objects.create(device_type=Device.DeviceType.KART_UNIT)
    cmd = DeviceCommand.objects.create(
        device=other_device,
        command_type=DeviceCommand.CommandType.SELF_TEST,
        requested_by=admin_user
    )
    
    url = reverse("device-commands-complete", kwargs={"pk": cmd.pk})
    api_client.credentials(HTTP_AUTHORIZATION=f"Device-Token {device_token}")
    response = api_client.post(url, {
        "status": DeviceCommand.Status.COMPLETED,
        "result": {"boot": True}
    }, format='json')
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
