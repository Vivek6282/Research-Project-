"""
Trackside — Unit tests for computed SessionSerializer fields (max_g, duration, kart).
"""

from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from tracks.models import Track
from driving_sessions.models import Session, Telemetry

User = get_user_model()


class TestSessionAggregation(APITestCase):

    def setUp(self):
        super().setUp()

        self.driver = User.objects.create_user(
            email="session_agg@trackside.local",
            name="Session Agg Driver",
            role="driver",
            password="Password123!",
        )

        self.track = Track.objects.create(
            name="Aggregation Track",
            kart_class=Track.KartClass.SPRINT,
        )

        self.now = timezone.now()

        # Session 1: completed, 38 min duration, kart #12, with telemetry records
        self.ended_session = Session.objects.create(
            driver=self.driver,
            track=self.track,
            kart_number="12",
            mode=Session.Mode.PERFORMANCE,
            started_at=self.now - timedelta(minutes=38),
            ended_at=self.now,
        )

        Telemetry.objects.create(
            session=self.ended_session,
            recorded_at=self.now - timedelta(minutes=30),
            lateral_g=1.12,
            speed_kmh=75.0,
            gps_lat=11.0,
            gps_lng=77.0,
            lap_number=1,
        )
        Telemetry.objects.create(
            session=self.ended_session,
            recorded_at=self.now - timedelta(minutes=15),
            lateral_g=1.42,
            speed_kmh=82.0,
            gps_lat=11.001,
            gps_lng=77.001,
            lap_number=2,
        )

        # Session 2: active session (ended_at is None)
        self.active_session = Session.objects.create(
            driver=self.driver,
            track=self.track,
            mode=Session.Mode.SAFETY,
            started_at=self.now - timedelta(minutes=10),
            ended_at=None,
        )

    def test_session_computed_max_g_and_duration(self):
        self.client.force_authenticate(user=self.driver)

        response = self.client.get(f"/api/sessions/{self.ended_session.id}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["duration"], "38 min")
        self.assertEqual(data["max_g"], "1.42g")
        self.assertEqual(data["kart"], "#12")
        self.assertEqual(data["laps"], 2)
        self.assertIsNone(data["best_lap"])

    def test_active_session_duration_is_in_progress(self):
        self.client.force_authenticate(user=self.driver)

        response = self.client.get(f"/api/sessions/{self.active_session.id}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["duration"], "In progress")
        self.assertIsNone(data["max_g"])
        self.assertIsNone(data["kart"])
        self.assertIsNone(data["laps"])
