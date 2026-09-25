"""
Trackside — Unit tests for Auto-Generated Username & Dual-Identifier Login.
"""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class TestUsernameAndDualIdentifierLogin(APITestCase):
    """Suite testing auto-generated usernames, optional driver email, and dual-identifier login."""

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email="admin_test@trackside.local",
            name="Test Admin",
            password="AdminPassword123!",
        )

    def test_back_to_back_driver_username_formatting(self):
        """Two Drivers created back-to-back get distinct, correctly-formatted usernames."""
        self.client.force_authenticate(user=self.admin_user)

        res1 = self.client.post(
            "/api/auth/users/",
            {
                "name": "Driver One",
                "role": "driver",
                "password": "Password123!",
            },
            format="json",
        )
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        u1_name = res1.data["username"]
        self.assertTrue(u1_name.startswith("TRK-DRV-"))
        self.assertEqual(len(u1_name), 14)  # TRK-DRV-000001

        res2 = self.client.post(
            "/api/auth/users/",
            {
                "name": "Driver Two",
                "role": "driver",
                "password": "Password123!",
            },
            format="json",
        )
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        u2_name = res2.data["username"]
        self.assertTrue(u2_name.startswith("TRK-DRV-"))
        self.assertNotEqual(u1_name, u2_name)

        # Verify sequence increments
        seq1 = int(u1_name.split("-")[-1])
        seq2 = int(u2_name.split("-")[-1])
        self.assertEqual(seq2, seq1 + 1)

    def test_driver_login_without_email_using_username(self):
        """A Driver created with no email can log in successfully using only generated username + password."""
        self.client.force_authenticate(user=self.admin_user)

        create_res = self.client.post(
            "/api/auth/users/",
            {
                "name": "No Email Driver",
                "role": "driver",
                "password": "DriverSecret123!",
            },
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        username = create_res.data["username"]

        # Log out admin & clear throttle cache
        self.client.logout()
        cache.clear()

        # Login using generated username
        login_res = self.client.post(
            "/api/auth/login/",
            {
                "identifier": username,
                "password": "DriverSecret123!",
            },
            format="json",
        )
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        self.assertEqual(login_res.data["username"], username)
        self.assertEqual(login_res.data["role"], "driver")

    def test_coach_creation_without_email_rejected(self):
        """A Coach account creation request without an email is rejected with a validation error."""
        self.client.force_authenticate(user=self.admin_user)

        res = self.client.post(
            "/api/auth/users/",
            {
                "name": "Emailless Coach",
                "role": "coach",
                "password": "CoachPassword123!",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", res.data)

    def test_client_passed_username_is_ignored(self):
        """Attempting to pass a username value in the request body is ignored."""
        self.client.force_authenticate(user=self.admin_user)

        res = self.client.post(
            "/api/auth/users/",
            {
                "name": "Hacker Driver",
                "role": "driver",
                "password": "Password123!",
                "username": "TRK-FAKE-999999",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(res.data["username"], "TRK-FAKE-999999")
        self.assertTrue(res.data["username"].startswith("TRK-DRV-"))
