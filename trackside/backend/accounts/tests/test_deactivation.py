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

    def test_created_user_persists_in_paginated_list_fetch(self, api_client, admin_user):
        """Creating a user and subsequently fetching GET /api/auth/users/ returns the created user in paginated results."""
        api_client.force_authenticate(user=admin_user)

        # 1. Create a new driver account
        create_res = api_client.post(
            "/api/auth/users/",
            {
                "name": "Persisted Driver Test",
                "email": "persisted@trackside.local",
                "role": "driver",
                "password": "DriverPassword123!",
            },
            format="json",
        )
        assert create_res.status_code == status.HTTP_201_CREATED
        created_id = create_res.data["id"]
        created_username = create_res.data["username"]

        # 2. Fetch GET /api/auth/users/
        list_res = api_client.get("/api/auth/users/")
        assert list_res.status_code == status.HTTP_200_OK

        # Handle DRF paginated structure
        results = list_res.data.get("results") if isinstance(list_res.data, dict) else list_res.data
        assert isinstance(results, list)

        # 3. Verify created user exists in results list
        matching = [u for u in results if u["id"] == created_id]
        assert len(matching) == 1
        assert matching[0]["name"] == "Persisted Driver Test"
        assert matching[0]["username"] == created_username

    def test_admin_cannot_deactivate_self(self, api_client, admin_user):
        """Admin user attempting to deactivate their own account via PATCH receives HTTP 400 Bad Request."""
        api_client.force_authenticate(user=admin_user)
        res = api_client.patch(
            f"/api/auth/users/{admin_user.id}/",
            {"is_active": False},
            format="json",
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "is_active" in res.data
        assert "cannot deactivate your own admin account" in str(res.data["is_active"])

    def test_update_existing_admin_account_with_admin_role_succeeds(self, api_client, admin_user):
        """Updating an existing Admin account while providing role='admin' succeeds and does not raise validation error."""
        api_client.force_authenticate(user=admin_user)
        res = api_client.patch(
            f"/api/auth/users/{admin_user.id}/",
            {"name": "Updated Admin Name", "role": "admin"},
            format="json",
        )
        assert res.status_code == status.HTTP_200_OK
        assert res.data["name"] == "Updated Admin Name"
        assert res.data["role"] == "admin"

    def test_seed_admin_reactivates_deactivated_admin(self, monkeypatch, db):
        """Running seed_admin management command reactivates an existing deactivated admin account."""
        from django.core.management import call_command

        # Create deactivated admin
        deact_admin = User.objects.create_superuser(
            email="seed_reactivate@trackside.local",
            name="Deactivated Seed Admin",
            password="SeedAdminPassword123!",
            is_active=False,
        )
        assert deact_admin.is_active is False

        monkeypatch.setenv("ADMIN_EMAIL", "seed_reactivate@trackside.local")
        monkeypatch.setenv("ADMIN_PASSWORD", "SeedAdminPassword123!")
        monkeypatch.setenv("ADMIN_NAME", "Deactivated Seed Admin")

        call_command("seed_admin")

        deact_admin.refresh_from_db()
        assert deact_admin.is_active is True

    def test_admin_can_delete_non_admin_user(self, api_client, admin_user, driver_user):
        """Admin can permanently delete a driver user via DELETE /api/auth/users/<id>/."""
        api_client.force_authenticate(user=admin_user)
        res = api_client.delete(f"/api/auth/users/{driver_user.id}/")
        assert res.status_code == status.HTTP_204_NO_CONTENT
        assert not User.objects.filter(id=driver_user.id).exists()

    def test_admin_cannot_delete_admin_user(self, api_client, admin_user):
        """Attempting to delete an Admin account via DELETE returns 400 Bad Request."""
        api_client.force_authenticate(user=admin_user)
        res = api_client.delete(f"/api/auth/users/{admin_user.id}/")
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert User.objects.filter(id=admin_user.id).exists()

    def test_non_admin_cannot_delete_user(self, api_client, coach_user, driver_user):
        """Non-admin user (Coach) attempting to delete a user receives 403 Forbidden."""
        api_client.force_authenticate(user=coach_user)
        res = api_client.delete(f"/api/auth/users/{driver_user.id}/")
        assert res.status_code == status.HTTP_403_FORBIDDEN
        assert User.objects.filter(id=driver_user.id).exists()


