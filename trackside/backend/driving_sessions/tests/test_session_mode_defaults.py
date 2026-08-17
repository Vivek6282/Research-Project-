"""
Trackside — Unit tests for Session mode-based threshold suggestions.

Verifies that Safety Mode sessions suggest 1.0g (conservative)
and Performance Mode sessions suggest 1.5g (pushing performance).
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from tracks.models import Track
from driving_sessions.models import Session

User = get_user_model()


class TestSessionModeDefaults(APITestCase):

    def setUp(self):
        super().setUp()

        self.driver = User.objects.create_user(
            email="driver_mode@trackside.local",
            name="Driver Mode Test",
            role="driver",
            password="Password123!",
        )

        self.track = Track.objects.create(
            name="Kari Motor Speedway",
            kart_class=Track.KartClass.SPRINT,
        )

        self.safety_session = Session.objects.create(
            driver=self.driver,
            track=self.track,
            mode=Session.Mode.SAFETY,
            started_at=timezone.now(),
        )

        self.performance_session = Session.objects.create(
            driver=self.driver,
            track=self.track,
            mode=Session.Mode.PERFORMANCE,
            started_at=timezone.now(),
        )

    def test_safety_mode_defaults_to_1_0g(self):
        self.assertEqual(self.safety_session.default_suggested_threshold, 1.0)

    def test_performance_mode_defaults_to_1_5g(self):
        self.assertEqual(self.performance_session.default_suggested_threshold, 1.5)

    def test_api_returns_default_suggested_threshold(self):
        self.client.force_authenticate(user=self.driver)
        response = self.client.get(f"/api/sessions/{self.safety_session.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["default_suggested_threshold"], 1.0)

        response2 = self.client.get(f"/api/sessions/{self.performance_session.id}/")
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response2.json()["default_suggested_threshold"], 1.5)
