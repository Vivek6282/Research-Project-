"""
Trackside — Unit tests for Driver Alert Summary API and Driver Data Isolation.
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from tracks.models import Track, Zone
from driving_sessions.models import Session, Alert, Telemetry
from driving_sessions.serializers import SessionSerializer

User = get_user_model()


class TestDriverAlertSummaryDataIsolation(APITestCase):

    def setUp(self):
        super().setUp()

        # Create two separate Driver accounts
        self.driver_a = User.objects.create_user(
            email="driver_a@trackside.local",
            name="Driver Alpha",
            role="driver",
            password="Password123!",
        )

        self.driver_b = User.objects.create_user(
            email="driver_b@trackside.local",
            name="Driver Beta",
            role="driver",
            password="Password123!",
        )

        # Create Track and Zones
        self.track = Track.objects.create(name="Apex Circuit Test Track")
        self.zone_hairpin = Zone.objects.create(
            track=self.track, label="Hairpin", threshold_g=1.15
        )
        self.zone_sweeper = Zone.objects.create(
            track=self.track, label="Sweeper", threshold_g=1.25
        )
        self.zone_chicane = Zone.objects.create(
            track=self.track, label="Chicane", threshold_g=1.10
        )

        # Create Sessions for Driver A
        self.session_a = Session.objects.create(
            driver=self.driver_a,
            track=self.track,
            mode=Session.Mode.SAFETY,
            goal_text="Zero Red Alerts at Hairpin",
            goal_passed=False,
            started_at=timezone.now(),
        )

        # Create Alerts for Driver A (4 alerts in Hairpin, 0 in Sweeper)
        for _ in range(4):
            Alert.objects.create(
                session=self.session_a,
                zone=self.zone_hairpin,
                severity=Alert.Severity.RED,
                g_value=1.28,
                threshold_applied=1.15,
                triggered_at=timezone.now(),
            )

        # Create Session for Driver B
        self.session_b = Session.objects.create(
            driver=self.driver_b,
            track=self.track,
            mode=Session.Mode.PERFORMANCE,
            goal_text="Clean run through Sweeper",
            goal_passed=True,
            started_at=timezone.now(),
        )

        # Create Alerts for Driver B (2 alerts in Sweeper, 0 in Hairpin)
        for _ in range(2):
            Alert.objects.create(
                session=self.session_b,
                zone=self.zone_sweeper,
                severity=Alert.Severity.AMBER,
                g_value=1.20,
                threshold_applied=1.25,
                triggered_at=timezone.now(),
            )

    def test_driver_a_sees_only_driver_a_summary(self):
        self.client.force_authenticate(user=self.driver_a)
        response = self.client.get("/api/sessions/alerts/summary/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["has_sessions"] is True
        assert data["total_sessions"] == 1

        # Verify zone alert breakdown for Driver A
        zones_by_name = {z["name"]: z for z in data["zones"]}
        assert zones_by_name["Hairpin"]["count"] == 4
        assert zones_by_name["Hairpin"]["status"] == "High Risk"
        assert zones_by_name["Sweeper"]["count"] == 0
        assert zones_by_name["Sweeper"]["status"] == "Clean"

        # Verify session goal for Driver A
        assert data["latest_session"]["goal_text"] == "Zero Red Alerts at Hairpin"
        assert data["latest_session"]["goal_passed"] is False

    def test_driver_b_sees_only_driver_b_summary(self):
        self.client.force_authenticate(user=self.driver_b)
        response = self.client.get("/api/sessions/alerts/summary/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["has_sessions"] is True
        assert data["total_sessions"] == 1

        # Verify zone alert breakdown for Driver B
        zones_by_name = {z["name"]: z for z in data["zones"]}
        assert zones_by_name["Hairpin"]["count"] == 0
        assert zones_by_name["Hairpin"]["status"] == "Clean"
        assert zones_by_name["Sweeper"]["count"] == 2
        assert zones_by_name["Sweeper"]["status"] == "Caution"

        # Verify session goal for Driver B
        assert data["latest_session"]["goal_text"] == "Clean run through Sweeper"
        assert data["latest_session"]["goal_passed"] is True

    def test_driver_without_sessions_receives_empty_state(self):
        new_driver = User.objects.create_user(
            email="driver_new@trackside.local",
            name="Driver Newbie",
            role="driver",
            password="Password123!",
        )

        self.client.force_authenticate(user=new_driver)
        response = self.client.get("/api/sessions/alerts/summary/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["has_sessions"] is False
        assert data["total_sessions"] == 0
        assert data["zones"] == []
        assert data["latest_session"] is None



class TestDriverSummaryMatchesCoachView(APITestCase):
    """The driver's summary carries the same live state, laps and alerts the coach sees for that run."""

    def setUp(self):
        self.driver = User.objects.create_user(email="sync_driver@trackside.local", name="Sync Driver",
                                               role="driver", password="Password123!")
        self.track = Track.objects.create(name="Sync Track")
        self.zone = Zone.objects.create(track=self.track, label="Hairpin", threshold_g=1.2)
        self.session = Session.objects.create(driver=self.driver, track=self.track, mode=Session.Mode.SAFETY,
                                              started_at=timezone.now())

    def summary(self):
        """The driver's own summary answer."""
        self.client.force_authenticate(user=self.driver)
        return self.client.get("/api/sessions/alerts/summary/").json()

    def test_open_run_with_recent_readings_is_live_with_laps_and_alerts(self):
        """A run with fresh readings reads live; its laps and alert count match the session itself."""
        for lap in (1, 2):
            Telemetry.objects.create(session=self.session, zone=self.zone, lateral_g=0.5, speed_kmh=50,
                                     gps_lat=0, gps_lng=0, recorded_at=timezone.now(), lap_number=lap)
        Alert.objects.create(session=self.session, zone=self.zone, severity=Alert.Severity.RED, g_value=1.3,
                             threshold_applied=1.2, triggered_at=timezone.now())
        latest = self.summary()["latest_session"]
        self.assertTrue(latest["live"])
        self.assertIsNone(latest["ended_at"])
        self.assertEqual(latest["alert_count"], 1)
        self.assertEqual(latest["laps"], SessionSerializer(self.session).data["laps"])

    def test_ended_run_is_not_live(self):
        """After the run is finished the driver sees it as ended, not live."""
        Telemetry.objects.create(session=self.session, zone=self.zone, lateral_g=0.5, speed_kmh=50,
                                 gps_lat=0, gps_lng=0, recorded_at=timezone.now(), lap_number=1)
        self.session.ended_at = timezone.now()
        self.session.save()
        latest = self.summary()["latest_session"]
        self.assertFalse(latest["live"])
        self.assertIsNotNone(latest["ended_at"])

    def test_same_named_corners_on_two_tracks_make_one_tile(self):
        """Sessions on two maps with the same corner names give one tile per name, alerts added up."""
        copy = Track.objects.create(name="Sync Track copy")
        copy_zone = Zone.objects.create(track=copy, label="Hairpin", threshold_g=0.9)
        newer = Session.objects.create(driver=self.driver, track=copy, mode=Session.Mode.SAFETY,
                                       started_at=timezone.now() + timedelta(minutes=1))
        for session, zone in ((self.session, self.zone), (newer, copy_zone)):
            Alert.objects.create(session=session, zone=zone, severity=Alert.Severity.AMBER, g_value=1.0,
                                 threshold_applied=1.2, triggered_at=timezone.now())
        tiles = [z for z in self.summary()["zones"] if z["name"] == "Hairpin"]
        self.assertEqual(len(tiles), 1)
        self.assertEqual(tiles[0]["count"], 2)
        self.assertEqual(tiles[0]["threshold"], 0.9)   # the limit of the latest run's map
