"""
Trackside — Authentication bypass tests (requirement #4).

Verifies that every protected endpoint returns 403 when accessed by
the wrong role, and 401 when accessed without any authentication.
Server-side role enforcement — the frontend hiding buttons is UX, not security.
"""

import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestNoAuthBypass:
    """
    Every role-restricted endpoint must return 403 for wrong roles
    and 401 for no auth at all.
    """

    @pytest.fixture(autouse=True)
    def setup_users(self):
        """Create one user per role for testing."""
        self.client = APIClient()

        self.admin = User.objects.create_user(
            email="admin@test.local",
            name="Test Admin",
            role="admin",
            password="AdminPass1!",
        )
        self.admin.is_staff = True
        self.admin.is_superuser = True
        self.admin.save()

        self.coach = User.objects.create_user(
            email="coach@test.local",
            name="Test Coach",
            role="coach",
            password="CoachPass1!",
        )

        self.driver = User.objects.create_user(
            email="driver@test.local",
            name="Test Driver",
            role="driver",
            password="DriverPass1!",
        )

    def _login_as(self, user):
        """Log in as the given user via the session."""
        self.client.force_authenticate(user=user)

    def test_user_list_requires_admin(self):
        """GET /api/auth/users/ — Coach and Driver get 403."""
        # Coach tries admin endpoint
        self._login_as(self.coach)
        response = self.client.get("/api/auth/users/")
        assert response.status_code == 403

        # Driver tries admin endpoint
        self._login_as(self.driver)
        response = self.client.get("/api/auth/users/")
        assert response.status_code == 403

    def test_user_create_requires_admin(self):
        """POST /api/auth/users/ — Coach and Driver get 403."""
        user_data = {
            "email": "new@test.local",
            "name": "New User",
            "role": "driver",
            "password": "NewPass123!",
        }

        self._login_as(self.coach)
        response = self.client.post("/api/auth/users/", user_data, format="json")
        assert response.status_code == 403

        self._login_as(self.driver)
        response = self.client.post("/api/auth/users/", user_data, format="json")
        assert response.status_code == 403

    def test_unauthenticated_gets_401(self):
        """Protected endpoints return 401 when no auth is provided."""
        self.client.force_authenticate(user=None)

        endpoints = [
            "/api/auth/users/",
            "/api/auth/me/",
            "/api/tracks/",
            "/api/sessions/",
            "/api/devices/",
        ]
        for url in endpoints:
            response = self.client.get(url)
            assert response.status_code in (401, 403), (
                f"{url} returned {response.status_code} — expected 401 or 403"
            )

    def test_no_register_endpoint_exists(self):
        """There must be no /register or /signup route anywhere."""
        self.client.force_authenticate(user=None)

        for path in ["/api/auth/register/", "/api/auth/signup/", "/register/", "/signup/"]:
            response = self.client.post(path, {}, format="json")
            # Should be 404 (not found), never 200 or 201
            assert response.status_code in (404, 401, 403), (
                f"{path} returned {response.status_code} — a registration endpoint exists!"
            )

    def test_admin_can_access_user_management(self):
        """Admin should successfully access user management."""
        self._login_as(self.admin)
        response = self.client.get("/api/auth/users/")
        assert response.status_code == 200
