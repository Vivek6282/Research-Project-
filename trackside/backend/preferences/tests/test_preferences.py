"""
Trackside — Unit tests for UserPreferences API.

Verifies that UserPreferences only accepts font_size and tutorial_completed,
and theme field is removed from model and API serializer responses.
"""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class TestUserPreferences(APITestCase):

    def setUp(self):
        super().setUp()

        self.user = User.objects.create_user(
            email="pref_user@trackside.local",
            name="Preference Test User",
            role="driver",
            password="Password123!",
        )

    def test_get_preferences_returns_font_size_without_theme(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/preferences/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertIn("font_size", data)
        self.assertIn("tutorial_completed", data)
        self.assertNotIn("theme", data)
        self.assertEqual(data["font_size"], "medium")

    def test_patch_preferences_updates_font_size(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            "/api/preferences/me/",
            {"font_size": "large"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["font_size"], "large")

        # Reload from DB
        self.user.preferences.refresh_from_db()
        self.assertEqual(self.user.preferences.font_size, "large")

    def test_patch_preferences_ignores_deprecated_theme_field(self):
        self.client.force_authenticate(user=self.user)

        # Attempting to send 'theme' field has no effect and is not present in response
        response = self.client.patch(
            "/api/preferences/me/",
            {"theme": "light", "font_size": "xlarge"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertNotIn("theme", data)
        self.assertEqual(data["font_size"], "xlarge")
