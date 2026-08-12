"""
Trackside — Unit tests for Account Deactivation & Login Prevention.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        email="admin_deact@trackside.local",
        name="Admin User",
        password="AdminPassword123!",
    )


@pytest.fixture
def coach_user(db):
    return User.objects.create_user(
        email="coach_deact@trackside.local",
        name="Coach User",
        role="coach",
        password="CoachPassword123!",
    )


@pytest.fixture
def driver_user(db):
    return User.objects.create_user(
        email="driver_deact@trackside.local",
        name="Driver User",
        role="driver",
        password="DriverPassword123!",
    )


@pytest.mark.django_db
class TestUserDeactivationAndLoginPrevention:
    """Suite verifying Admin-only deactivation enforcement and login blocking for deactivated users."""

    def test_deactivate_user_requires_admin_role(self, api_client, admin_user, coach_user, driver_user):
        """Only Admin can deactivate users via PATCH /api/auth/users/<id>/; non-admins get 403."""
        # Non-admin (Coach) attempting to deactivate Driver -> 403 Forbidden
        api_client.force_authenticate(user=coach_user)
        res_forbidden = api_client.patch(
            f"/api/auth/users/{driver_user.id}/",
            {"is_active": False},
            format="json",
        )
        assert res_forbidden.status_code == status.HTTP_403_FORBIDDEN

        # Admin deactivating Driver -> 200 OK
        api_client.force_authenticate(user=admin_user)
        res_ok = api_client.patch(
            f"/api/auth/users/{driver_user.id}/",
            {"is_active": False},
            format="json",
        )
        assert res_ok.status_code == status.HTTP_200_OK
        assert res_ok.data["is_active"] is False

        # Reload driver_user from db
        driver_user.refresh_from_db()
        assert driver_user.is_active is False

    def test_deactivated_user_cannot_login(self, api_client, admin_user, driver_user):
        """A deactivated user attempting to log in receives HTTP 401 Unauthorized."""
        # Deactivate driver
        driver_user.is_active = False
        driver_user.save()

        # Attempt login
        from django.core.cache import cache
        cache.clear()

        res = api_client.post(
            "/api/auth/login/",
            {
                "identifier": driver_user.username or driver_user.email,
                "password": "DriverPassword123!",
            },
            format="json",
        )
        assert res.status_code == status.HTTP_401_UNAUTHORIZED
        assert res.data["detail"] == "This account has been deactivated."
