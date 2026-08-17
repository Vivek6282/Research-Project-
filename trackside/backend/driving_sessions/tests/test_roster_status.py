"""
Trackside — Unit tests for Roster Status API & Trajectory Stage Classification.
"""

from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from tracks.models import Track, Zone
from driving_sessions.models import Session, Telemetry

User = get_user_model()


class TestRosterStatusView(APITestCase):

    def setUp(self):
        super().setUp()

        self.coach = User.objects.create_user(
            email="coach_roster@trackside.local",
            name="Coach Roster Test",
            role="coach",
            password="Password123!",
        )

        self.driver_a = User.objects.create_user(
            email="driver_roster_a@trackside.local",
            name="Driver Roster Alpha",
            role="driver",
            password="Password123!",
        )

        self.driver_b = User.objects.create_user(
            email="driver_roster_b@trackside.local",
            name="Driver Roster Beta",
            role="driver",
            password="Password123!",
        )

        self.track = Track.objects.create(name="Apex Test Circuit")
        self.zone_hairpin = Zone.objects.create(
            track=self.track, label="Hairpin", threshold_g=1.15
        )

        # Session & Intervene telemetry reading for Driver A (g=1.25 >= 1.15 threshold => intervene)
        self.session_a = Session.objects.create(
            driver=self.driver_a,
            track=self.track,
            mode=Session.Mode.PERFORMANCE,
            started_at=timezone.now(),
        )
        Telemetry.objects.create(
            session=self.session_a,
            zone=self.zone_hairpin,
            recorded_at=timezone.now(),
            lateral_g=1.25,
            speed_kmh=82.0,
            gps_lat=11.016842,
            gps_lng=76.955831,
        )

        # Session & Nominal telemetry reading for Driver B (g=0.70 < 1.15 threshold => nominal)
        self.session_b = Session.objects.create(
            driver=self.driver_b,
            track=self.track,
            mode=Session.Mode.SAFETY,
            started_at=timezone.now(),
        )
        Telemetry.objects.create(
            session=self.session_b,
            zone=self.zone_hairpin,
            recorded_at=timezone.now(),
            lateral_g=0.70,
            speed_kmh=75.0,
            gps_lat=11.016842,
            gps_lng=76.955831,
        )

    def test_coach_receives_full_roster_status_with_stages(self):
        self.client.force_authenticate(user=self.coach)
        response = self.client.get("/api/sessions/roster-status/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "roster" in data
        assert len(data["roster"]) >= 2

        driver_map = {d["driver_name"]: d for d in data["roster"]}
        assert "Driver Roster Alpha" in driver_map
        assert "Driver Roster Beta" in driver_map

        # Verify Driver A stage classification is intervene
        assert driver_map["Driver Roster Alpha"]["current_g"] == 1.25
        assert driver_map["Driver Roster Alpha"]["stage"] == "intervene"

        # Verify Driver B stage classification is nominal
        assert driver_map["Driver Roster Beta"]["current_g"] == 0.70
        assert driver_map["Driver Roster Beta"]["stage"] == "nominal"

    def test_driver_receives_only_self_roster_status(self):
        self.client.force_authenticate(user=self.driver_a)
        response = self.client.get("/api/sessions/roster-status/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "roster" in data
        assert len(data["roster"]) == 1
        assert data["roster"][0]["driver_name"] == "Driver Roster Alpha"
