"""
Trackside — Unit tests for Roster Status API & Trajectory Stage Classification.
"""

from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from tracks.models import Track, Zone
from driving_sessions.models import Session, Telemetry

User = get_user_model()


class TestRosterStatusView(APITestCase):

    def setUp(self):
        # Initializes test coach, test drivers, tracks, zones, and baseline telemetry.
        super().setUp()
        self.coach = User.objects.create_user(
            email="coach_roster@trackside.local", name="Coach Roster Test", role="coach", password="Password123!"
        )
        self.driver_a = User.objects.create_user(
            email="driver_roster_a@trackside.local", name="Driver Roster Alpha", role="driver", password="Password123!"
        )
        self.driver_b = User.objects.create_user(
            email="driver_roster_b@trackside.local", name="Driver Roster Beta", role="driver", password="Password123!"
        )
        self.track = Track.objects.create(name="Apex Test Circuit")
        self.zone_hairpin = Zone.objects.create(track=self.track, label="Hairpin", threshold_g=1.15)

        # Session & Intervene telemetry for Driver A (g=1.25 >= 1.15 => intervene)
        self.session_a = Session.objects.create(
            driver=self.driver_a, track=self.track, mode=Session.Mode.PERFORMANCE, started_at=timezone.now()
        )
        Telemetry.objects.create(
            session=self.session_a, zone=self.zone_hairpin, recorded_at=timezone.now(),
            lateral_g=1.25, speed_kmh=82.0, gps_lat=11.016842, gps_lng=76.955831
        )

        # Session & Nominal telemetry for Driver B (g=0.70 < 1.15 => nominal)
        self.session_b = Session.objects.create(
            driver=self.driver_b, track=self.track, mode=Session.Mode.SAFETY, started_at=timezone.now()
        )
        Telemetry.objects.create(
            session=self.session_b, zone=self.zone_hairpin, recorded_at=timezone.now(),
            lateral_g=0.70, speed_kmh=75.0, gps_lat=11.016842, gps_lng=76.955831
        )

    def test_coach_receives_full_roster_status_with_stages(self):
        # Verifies coach receives all active drivers with computed stages and real readings.
        self.client.force_authenticate(user=self.coach)
        response = self.client.get("/api/sessions/roster-status/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "roster" in data
        assert len(data["roster"]) >= 2

        driver_map = {d["driver_name"]: d for d in data["roster"]}
        assert "Driver Roster Alpha" in driver_map
        assert "Driver Roster Beta" in driver_map
        assert driver_map["Driver Roster Alpha"]["current_g"] == 1.25
        assert driver_map["Driver Roster Alpha"]["stage"] == "intervene"
        assert driver_map["Driver Roster Beta"]["current_g"] == 0.70
        assert driver_map["Driver Roster Beta"]["stage"] == "nominal"

    def test_driver_receives_only_self_roster_status(self):
        # Verifies a driver receives only their own entry in the roster status payload.
        self.client.force_authenticate(user=self.driver_a)
        response = self.client.get("/api/sessions/roster-status/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "roster" in data
        assert len(data["roster"]) == 1
        assert data["roster"][0]["driver_name"] == "Driver Roster Alpha"

    def test_driver_with_no_sessions_returns_empty_contract(self):
        # Verifies a driver without sessions returns no_data, session_state none, and no kart key.
        driver_c = User.objects.create_user(
            email="driver_c_empty@trackside.local", name="Driver Empty Roster", role="driver", password="Password123!"
        )
        self.client.force_authenticate(user=self.coach)
        response = self.client.get("/api/sessions/roster-status/")
        assert response.status_code == status.HTTP_200_OK

        driver_map = {d["driver_name"]: d for d in response.json()["roster"]}
        entry = driver_map["Driver Empty Roster"]

        assert entry["driver_id"] == str(driver_c.id)
        assert entry["driver_name"] == "Driver Empty Roster"
        assert entry["current_g"] is None
        assert entry["active_zone"] is None
        assert entry["active_threshold"] is None
        assert entry["stage"] == "no_data"
        assert entry["session_state"] == "none"
        assert entry["live"] is False
        assert "kart" not in entry

    def test_ended_session_state(self):
        # Verifies an ended session marks session_state as ended and live as false.
        driver_ended = User.objects.create_user(
            email="driver_ended@trackside.local", name="Driver Ended Test", role="driver", password="Password123!"
        )
        sess = Session.objects.create(
            driver=driver_ended, track=self.track, mode=Session.Mode.PERFORMANCE,
            started_at=timezone.now() - timedelta(minutes=10), ended_at=timezone.now() - timedelta(minutes=1)
        )
        Telemetry.objects.create(
            session=sess, zone=self.zone_hairpin, recorded_at=timezone.now() - timedelta(minutes=2),
            lateral_g=0.90, speed_kmh=80.0, gps_lat=11.016842, gps_lng=76.955831
        )

        self.client.force_authenticate(user=self.coach)
        response = self.client.get("/api/sessions/roster-status/")
        assert response.status_code == status.HTTP_200_OK

        driver_map = {d["driver_name"]: d for d in response.json()["roster"]}
        entry = driver_map["Driver Ended Test"]
        assert entry["session_state"] == "ended"
        assert entry["live"] is False

    def test_live_flag_fresh_telemetry(self):
        # Verifies telemetry younger than 30s in an active session sets live to true.
        driver_fresh = User.objects.create_user(
            email="driver_fresh@trackside.local", name="Driver Fresh Live", role="driver", password="Password123!"
        )
        sess = Session.objects.create(
            driver=driver_fresh, track=self.track, mode=Session.Mode.PERFORMANCE,
            started_at=timezone.now() - timedelta(minutes=5)
        )
        Telemetry.objects.create(
            session=sess, zone=self.zone_hairpin, recorded_at=timezone.now() - timedelta(seconds=10),
            lateral_g=1.05, speed_kmh=85.0, gps_lat=11.016842, gps_lng=76.955831
        )

        self.client.force_authenticate(user=self.coach)
        response = self.client.get("/api/sessions/roster-status/")
        assert response.status_code == status.HTTP_200_OK

        driver_map = {d["driver_name"]: d for d in response.json()["roster"]}
        entry = driver_map["Driver Fresh Live"]
        assert entry["session_state"] == "in_progress"
        assert entry["live"] is True

    def test_live_flag_stale_telemetry(self):
        # Verifies telemetry older than 30s in an active session sets live to false.
        driver_stale = User.objects.create_user(
            email="driver_stale@trackside.local", name="Driver Stale Live", role="driver", password="Password123!"
        )
        sess = Session.objects.create(
            driver=driver_stale, track=self.track, mode=Session.Mode.PERFORMANCE,
            started_at=timezone.now() - timedelta(minutes=10)
        )
        Telemetry.objects.create(
            session=sess, zone=self.zone_hairpin, recorded_at=timezone.now() - timedelta(seconds=45),
            lateral_g=0.85, speed_kmh=80.0, gps_lat=11.016842, gps_lng=76.955831
        )

        self.client.force_authenticate(user=self.coach)
        response = self.client.get("/api/sessions/roster-status/")
        assert response.status_code == status.HTTP_200_OK

        driver_map = {d["driver_name"]: d for d in response.json()["roster"]}
        entry = driver_map["Driver Stale Live"]
        assert entry["session_state"] == "in_progress"
        assert entry["live"] is False

    def test_real_telemetry_threshold_and_stage_computation(self):
        # Verifies exact g, active zone name, threshold, and monitoring stage calculation.
        driver_eval = User.objects.create_user(
            email="driver_eval@trackside.local", name="Driver Eval Test", role="driver", password="Password123!"
        )
        zone_chicane = Zone.objects.create(track=self.track, label="Chicane North", threshold_g=1.10)
        sess = Session.objects.create(
            driver=driver_eval, track=self.track, mode=Session.Mode.PERFORMANCE,
            started_at=timezone.now() - timedelta(minutes=2)
        )
        # 1.00 g / 1.10 g = 0.909 (between 0.82 and 1.0) => monitoring
        Telemetry.objects.create(
            session=sess, zone=zone_chicane, recorded_at=timezone.now() - timedelta(seconds=5),
            lateral_g=1.00, speed_kmh=78.0, gps_lat=11.016842, gps_lng=76.955831
        )

        self.client.force_authenticate(user=self.coach)
        response = self.client.get("/api/sessions/roster-status/")
        assert response.status_code == status.HTTP_200_OK

        driver_map = {d["driver_name"]: d for d in response.json()["roster"]}
        entry = driver_map["Driver Eval Test"]
        assert entry["current_g"] == 1.00
        assert entry["active_threshold"] == 1.10
        assert entry["active_zone"] == "Chicane North"
        assert entry["stage"] == "monitoring"

    def test_summary_endpoint_empty_goal_returns_null(self):
        # Verifies driver summary endpoint returns goal_passed: null when goal is empty.
        driver_goal = User.objects.create_user(
            email="driver_goal_null@trackside.local", name="Driver Goal Null", role="driver", password="Password123!"
        )
        Session.objects.create(
            driver=driver_goal, track=self.track, mode=Session.Mode.PERFORMANCE,
            started_at=timezone.now(), goal_text=""
        )

        self.client.force_authenticate(user=driver_goal)
        response = self.client.get("/api/sessions/alerts/summary/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["latest_session"]["goal_text"] == ""
        assert data["latest_session"]["goal_passed"] is None

    def test_security_s1_roster_access(self):
        # Verifies anonymous access is rejected with 401 and driver sees only self.
        response = self.client.get("/api/sessions/roster-status/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        self.client.force_authenticate(user=self.driver_b)
        response = self.client.get("/api/sessions/roster-status/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["roster"]) == 1
        assert data["roster"][0]["driver_name"] == "Driver Roster Beta"
