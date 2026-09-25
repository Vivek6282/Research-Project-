"""
Trackside — Unit tests for Account Deactivation & Login Prevention.
"""

import os
from unittest import mock
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class TestUserDeactivationAndLoginPrevention(APITestCase):
    """Suite verifying Admin-only deactivation enforcement and login blocking for deactivated users."""

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email="admin_deact@trackside.local",
            name="Admin User",
            password="AdminPassword123!",
        )
        self.coach_user = User.objects.create_user(
            email="coach_deact@trackside.local",
            name="Coach User",
            role="coach",
            password="CoachPassword123!",
        )
        self.driver_user = User.objects.create_user(
            email="driver_deact@trackside.local",
            name="Driver User",
            role="driver",
            password="DriverPassword123!",
        )

    def test_deactivate_user_requires_admin_role(self):
        """Only Admin can deactivate users via PATCH /api/auth/users/<id>/; non-admins get 403."""
        # Non-admin (Coach) attempting to deactivate Driver -> 403 Forbidden
        self.client.force_authenticate(user=self.coach_user)
        res_forbidden = self.client.patch(
            f"/api/auth/users/{self.driver_user.id}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(res_forbidden.status_code, status.HTTP_403_FORBIDDEN)

        # Admin deactivating Driver -> 200 OK
        self.client.force_authenticate(user=self.admin_user)
        res_ok = self.client.patch(
            f"/api/auth/users/{self.driver_user.id}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(res_ok.status_code, status.HTTP_200_OK)
        self.assertFalse(res_ok.data["is_active"])

        # Reload driver_user from db
        self.driver_user.refresh_from_db()
        self.assertFalse(self.driver_user.is_active)

    def test_deactivated_user_cannot_login(self):
        """A deactivated user attempting to log in receives HTTP 401 Unauthorized."""
        # Deactivate driver
        self.driver_user.is_active = False
        self.driver_user.save()

        # Attempt login
        cache.clear()

        res = self.client.post(
            "/api/auth/login/",
            {
                "identifier": self.driver_user.username or self.driver_user.email,
                "password": "DriverPassword123!",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(res.data["detail"], "This account has been deactivated.")

    def test_created_user_persists_in_paginated_list_fetch(self):
        """Creating a user and subsequently fetching GET /api/auth/users/ returns the created user in paginated results."""
        self.client.force_authenticate(user=self.admin_user)

        # 1. Create a new driver account
        create_res = self.client.post(
            "/api/auth/users/",
            {
                "name": "Persisted Driver Test",
                "email": "persisted@trackside.local",
                "role": "driver",
                "password": "DriverPassword123!",
            },
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        created_id = create_res.data["id"]
        created_username = create_res.data["username"]

        # 2. Fetch GET /api/auth/users/
        list_res = self.client.get("/api/auth/users/")
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)

        # Handle DRF paginated structure
        results = list_res.data.get("results") if isinstance(list_res.data, dict) else list_res.data
        self.assertIsInstance(results, list)

        # 3. Verify created user exists in results list
        matching = [u for u in results if u["id"] == created_id]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["name"], "Persisted Driver Test")
        self.assertEqual(matching[0]["username"], created_username)

    def test_admin_cannot_deactivate_self(self):
        """Admin user attempting to deactivate their own account via PATCH receives HTTP 400 Bad Request."""
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.patch(
            f"/api/auth/users/{self.admin_user.id}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("is_active", res.data)
        self.assertIn("cannot deactivate your own admin account", str(res.data["is_active"]))

    def test_update_existing_admin_account_with_admin_role_succeeds(self):
        """Updating an existing Admin account while providing role='admin' succeeds and does not raise validation error."""
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.patch(
            f"/api/auth/users/{self.admin_user.id}/",
            {"name": "Updated Admin Name", "role": "admin"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "Updated Admin Name")
        self.assertEqual(res.data["role"], "admin")

    def test_seed_admin_reactivates_deactivated_admin(self):
        """Running seed_admin management command reactivates an existing deactivated admin account."""
        # Create deactivated admin
        deact_admin = User.objects.create_superuser(
            email="seed_reactivate@trackside.local",
            name="Deactivated Seed Admin",
            password="SeedAdminPassword123!",
            is_active=False,
        )
        self.assertFalse(deact_admin.is_active)

        with mock.patch.dict(os.environ, {
            "ADMIN_EMAIL": "seed_reactivate@trackside.local",
            "ADMIN_PASSWORD": "SeedAdminPassword123!",
            "ADMIN_NAME": "Deactivated Seed Admin",
        }):
            call_command("seed_admin")

        deact_admin.refresh_from_db()
        self.assertTrue(deact_admin.is_active)
        self.assertIsNotNone(deact_admin.username)
        self.assertTrue(deact_admin.username.startswith("TRK-ADMIN-"))

        # Also verify fresh seed_admin run generates TRK-ADMIN login ID
        with mock.patch.dict(os.environ, {
            "ADMIN_EMAIL": "seed_fresh_admin@trackside.local",
            "ADMIN_PASSWORD": "FreshAdminPass123!",
            "ADMIN_NAME": "Fresh Seed Admin",
        }):
            call_command("seed_admin")

        fresh_admin = User.objects.get(email="seed_fresh_admin@trackside.local")
        self.assertIsNotNone(fresh_admin.username)
        self.assertTrue(fresh_admin.username.startswith("TRK-ADMIN-"))

    def test_delete_user_returns_405_method_not_allowed(self):
        """DELETE /api/auth/users/<id>/ returns 405 Method Not Allowed to prevent cascading data loss."""
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.delete(f"/api/auth/users/{self.driver_user.id}/")
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(User.objects.filter(id=self.driver_user.id).exists())
