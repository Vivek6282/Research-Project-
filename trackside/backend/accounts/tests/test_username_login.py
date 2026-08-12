"""
Trackside — Unit tests for Auto-Generated Username & Dual-Identifier Login.
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
        email="admin_test@trackside.local",
        name="Test Admin",
        password="AdminPassword123!",
    )


@pytest.mark.django_db
class TestUsernameAndDualIdentifierLogin:
    """Suite testing auto-generated usernames, optional driver email, and dual-identifier login."""

    def test_back_to_back_driver_username_formatting(self, api_client, admin_user):
        """Two Drivers created back-to-back get distinct, correctly-formatted usernames."""
        api_client.force_authenticate(user=admin_user)

        res1 = api_client.post(
            "/api/auth/users/",
            {
                "name": "Driver One",
                "role": "driver",
                "password": "Password123!",
            },
            format="json",
        )
        assert res1.status_code == status.HTTP_201_CREATED
        u1_name = res1.data["username"]
        assert u1_name.startswith("TRK-DRV-")
        assert len(u1_name) == 14  # TRK-DRV-000001

        res2 = api_client.post(
            "/api/auth/users/",
            {
                "name": "Driver Two",
                "role": "driver",
                "password": "Password123!",
            },
            format="json",
        )
        assert res2.status_code == status.HTTP_201_CREATED
        u2_name = res2.data["username"]
        assert u2_name.startswith("TRK-DRV-")
        assert u1_name != u2_name

        # Verify sequence increments
        seq1 = int(u1_name.split("-")[-1])
        seq2 = int(u2_name.split("-")[-1])
        assert seq2 == seq1 + 1

    def test_driver_login_without_email_using_username(self, api_client, admin_user):
        """A Driver created with no email can log in successfully using only generated username + password."""
        api_client.force_authenticate(user=admin_user)

        create_res = api_client.post(
            "/api/auth/users/",
            {
                "name": "No Email Driver",
                "role": "driver",
                "password": "DriverSecret123!",
            },
            format="json",
        )
        assert create_res.status_code == status.HTTP_201_CREATED
        username = create_res.data["username"]

        # Log out admin & clear throttle cache
        api_client.logout()
        from django.core.cache import cache
        cache.clear()

        # Login using generated username
        login_res = api_client.post(
            "/api/auth/login/",
            {
                "identifier": username,
                "password": "DriverSecret123!",
            },
            format="json",
        )
        assert login_res.status_code == status.HTTP_200_OK
        assert login_res.data["username"] == username
        assert login_res.data["role"] == "driver"

    def test_coach_creation_without_email_rejected(self, api_client, admin_user):
        """A Coach account creation request without an email is rejected with a validation error."""
        api_client.force_authenticate(user=admin_user)

        res = api_client.post(
            "/api/auth/users/",
            {
                "name": "Emailless Coach",
                "role": "coach",
                "password": "CoachPassword123!",
            },
            format="json",
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in res.data

    def test_client_passed_username_is_ignored(self, api_client, admin_user):
        """Attempting to pass a username value in the request body is ignored."""
        api_client.force_authenticate(user=admin_user)

        res = api_client.post(
            "/api/auth/users/",
            {
                "name": "Hacker Driver",
                "role": "driver",
                "password": "Password123!",
                "username": "TRK-FAKE-999999",
            },
            format="json",
        )
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["username"] != "TRK-FAKE-999999"
        assert res.data["username"].startswith("TRK-DRV-")
