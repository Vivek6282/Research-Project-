"""
Trackside — Tests for telemetry ingestion, validation, authorization, and server-side alerts.
"""

from datetime import datetime, timezone, timedelta
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from tracks.models import Track, Zone
from devices.models import Device
from drivers.models import DriverZoneThreshold
from driving_sessions.models import Session, Telemetry, Alert

User = get_user_model()


class TestTelemetryAlerts(APITestCase):

    def setUp(self):
        super().setUp()
        self.driver = User.objects.create_user(
            email="telemetry_driver@trackside.local",
            name="Telemetry Driver",
            role="driver",
            password="DriverPassword123!",
        )
        self.other_driver = User.objects.create_user(
            email="other_driver@trackside.local",
            name="Other Driver",
            role="driver",
            password="DriverPassword123!",
        )

        self.track = Track.objects.create(
            name="Alert Test Circuit",
            kart_class=Track.KartClass.SPRINT,
        )
        self.zone_hairpin = Zone.objects.create(
            track=self.track,
            label="Hairpin",
            threshold_g=1.15,
            corner_type=Zone.CornerType.HAIRPIN,
        )
        self.zone_chicane = Zone.objects.create(
            track=self.track,
            label="Chicane",
            threshold_g=1.30,
            corner_type=Zone.CornerType.CHICANE,
        )

        self.now = datetime(2026, 10, 16, 10, 0, 0, tzinfo=timezone.utc)

        self.session = Session.objects.create(
            driver=self.driver,
            track=self.track,
            mode=Session.Mode.SAFETY,
            kart_number="demo",
            started_at=self.now,
        )
        self.other_session = Session.objects.create(
            driver=self.other_driver,
            track=self.track,
            mode=Session.Mode.SAFETY,
            kart_number="demo-2",
            started_at=self.now,
        )

        # Device assigned to self.driver
        self.device = Device.objects.create(
            device_type=Device.DeviceType.KART_UNIT,
            assigned_to=self.driver,
        )
        self.raw_token = self.device.set_api_key()
        self.device.save()

    def as_kart_unit(self):
        """Send as the driver's kart unit (Phase 2.1: a driver's own sign-in is the phone page, real-time only)."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Device-Token {self.raw_token}")

    def test_lap_number_stored_and_missing_recorded_at_gives_400(self):
        """lap_number is stored; a missing recorded_at gives 400; lap_number < 1 gives 400."""
        self.as_kart_unit()

        # 1. Valid telemetry with lap_number
        payload = {
            "recorded_at": (self.now + timedelta(seconds=1)).isoformat(),
            "lateral_g": 0.85,
            "speed_kmh": 60.0,
            "gps_lat": 12.9716,
            "gps_lng": 77.5946,
            "lap_number": 2,
        }
        res = self.client.post(
            f"/api/sessions/{self.session.id}/telemetry/",
            payload,
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.json()["lap_number"], 2)
        telemetry = Telemetry.objects.get(id=res.json()["id"])
        self.assertEqual(telemetry.lap_number, 2)

        # 2. Missing recorded_at -> 400
        bad_payload = {
            "lateral_g": 0.85,
            "speed_kmh": 60.0,
            "gps_lat": 12.9716,
            "gps_lng": 77.5946,
            "lap_number": 2,
        }
        bad_res = self.client.post(
            f"/api/sessions/{self.session.id}/telemetry/",
            bad_payload,
            format="json",
        )
        self.assertEqual(bad_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("recorded_at", bad_res.json())

        # 3. lap_number < 1 -> 400
        invalid_lap = {
            "recorded_at": (self.now + timedelta(seconds=2)).isoformat(),
            "lateral_g": 0.85,
            "speed_kmh": 60.0,
            "gps_lat": 12.9716,
            "gps_lng": 77.5946,
            "lap_number": 0,
        }
        res_zero = self.client.post(
            f"/api/sessions/{self.session.id}/telemetry/",
            invalid_lap,
            format="json",
        )
        self.assertEqual(res_zero.status_code, status.HTTP_400_BAD_REQUEST)

    def test_alert_crossing_stages_transitions_and_straight_resets(self):
        """
        - Batch crossing amber then red creates exactly 2 alerts.
        - Staying red creates none.
        - Dropping and re-crossing creates a new one.
        - A straight resets.
        - State carries across two requests.
        """
        self.as_kart_unit()
        thresh = self.zone_hairpin.threshold_g  # 1.15 -> amber at >= 0.943, red at >= 1.15

        # Request 1:
        # 1. Straight (zone=None, g=0.5)
        # 2. Amber (zone=Hairpin, g=1.00) -> creates AMBER alert (1)
        # 3. Red (zone=Hairpin, g=1.20) -> creates RED alert (2)
        # 4. Staying Red (zone=Hairpin, g=1.25) -> creates none
        batch1 = [
            {
                "recorded_at": (self.now + timedelta(seconds=1)).isoformat(),
                "lateral_g": 0.50,
                "speed_kmh": 70.0,
                "gps_lat": 12.9716,
                "gps_lng": 77.5946,
                "zone": None,
            },
            {
                "recorded_at": (self.now + timedelta(seconds=2)).isoformat(),
                "lateral_g": 1.00,
                "speed_kmh": 65.0,
                "gps_lat": 12.9717,
                "gps_lng": 77.5947,
                "zone": str(self.zone_hairpin.id),
            },
            {
                "recorded_at": (self.now + timedelta(seconds=3)).isoformat(),
                "lateral_g": 1.20,
                "speed_kmh": 60.0,
                "gps_lat": 12.9718,
                "gps_lng": 77.5948,
                "zone": str(self.zone_hairpin.id),
            },
            {
                "recorded_at": (self.now + timedelta(seconds=4)).isoformat(),
                "lateral_g": 1.25,
                "speed_kmh": 58.0,
                "gps_lat": 12.9719,
                "gps_lng": 77.5949,
                "zone": str(self.zone_hairpin.id),
            },
        ]
        res1 = self.client.post(
            f"/api/sessions/{self.session.id}/telemetry/",
            batch1,
            format="json",
        )
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        alerts_r1 = list(Alert.objects.filter(session=self.session).order_by("triggered_at"))
        self.assertEqual(len(alerts_r1), 2)
        self.assertEqual(alerts_r1[0].severity, Alert.Severity.AMBER)
        self.assertEqual(alerts_r1[0].g_value, 1.00)
        self.assertEqual(alerts_r1[0].threshold_applied, thresh)
        self.assertEqual(alerts_r1[1].severity, Alert.Severity.RED)
        self.assertEqual(alerts_r1[1].g_value, 1.20)
        self.assertEqual(alerts_r1[1].threshold_applied, thresh)

        # Request 2 (State carries across requests):
        # 5. Still Red (g=1.22) -> should NOT create alert because prev reading was Red
        # 6. Dropping below amber (g=0.60, hairpin) -> resets state, creates no alert
        # 7. Re-crossing to Red (g=1.24, hairpin) -> creates new RED alert (3)
        # 8. Straight (zone=None, g=0.50) -> resets state
        # 9. Re-crossing to Amber (g=1.02, hairpin) -> creates new AMBER alert (4)
        batch2 = [
            {
                "recorded_at": (self.now + timedelta(seconds=5)).isoformat(),
                "lateral_g": 1.22,
                "speed_kmh": 57.0,
                "gps_lat": 12.9720,
                "gps_lng": 77.5950,
                "zone": str(self.zone_hairpin.id),
            },
            {
                "recorded_at": (self.now + timedelta(seconds=6)).isoformat(),
                "lateral_g": 0.60,
                "speed_kmh": 55.0,
                "gps_lat": 12.9721,
                "gps_lng": 77.5951,
                "zone": str(self.zone_hairpin.id),
            },
            {
                "recorded_at": (self.now + timedelta(seconds=7)).isoformat(),
                "lateral_g": 1.24,
                "speed_kmh": 54.0,
                "gps_lat": 12.9722,
                "gps_lng": 77.5952,
                "zone": str(self.zone_hairpin.id),
            },
            {
                "recorded_at": (self.now + timedelta(seconds=8)).isoformat(),
                "lateral_g": 0.50,
                "speed_kmh": 70.0,
                "gps_lat": 12.9723,
                "gps_lng": 77.5953,
                "zone": None,
            },
            {
                "recorded_at": (self.now + timedelta(seconds=9)).isoformat(),
                "lateral_g": 1.02,
                "speed_kmh": 62.0,
                "gps_lat": 12.9724,
                "gps_lng": 77.5954,
                "zone": str(self.zone_hairpin.id),
            },
        ]
        res2 = self.client.post(
            f"/api/sessions/{self.session.id}/telemetry/",
            batch2,
            format="json",
        )
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)

        alerts_all = list(Alert.objects.filter(session=self.session).order_by("triggered_at"))
        # Expected: 4 alerts total (amber, red, red, amber)
        self.assertEqual(len(alerts_all), 4)
        self.assertEqual(alerts_all[2].severity, Alert.Severity.RED)
        self.assertEqual(alerts_all[2].g_value, 1.24)
        self.assertEqual(alerts_all[3].severity, Alert.Severity.AMBER)
        self.assertEqual(alerts_all[3].g_value, 1.02)

    def test_threshold_applied_is_the_zone_limit_and_per_driver_rows_are_ignored(self):
        """threshold_applied is the zone's own limit (set on the map); old per-driver rows are present but ignored."""
        self.as_kart_unit()

        # Old per-driver rows (history): an older 1.10 and a newer 1.02, both ignored now
        t1 = DriverZoneThreshold.objects.create(
            driver=self.driver,
            zone=self.zone_hairpin,
            custom_threshold_g=1.10,
        )
        t2 = DriverZoneThreshold.objects.create(
            driver=self.driver,
            zone=self.zone_hairpin,
            custom_threshold_g=1.02,
        )

        reading = {
            "recorded_at": (self.now + timedelta(seconds=1)).isoformat(),
            "lateral_g": 1.05,  # >= 0.82 x 1.15 but < 1.15 -> AMBER under the zone's limit (RED under the ignored 1.02)
            "speed_kmh": 60.0,
            "gps_lat": 12.9716,
            "gps_lng": 77.5946,
            "zone": str(self.zone_hairpin.id),
        }
        res = self.client.post(
            f"/api/sessions/{self.session.id}/telemetry/",
            reading,
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        alert = Alert.objects.filter(session=self.session).first()
        self.assertIsNotNone(alert)
        self.assertEqual(alert.severity, Alert.Severity.AMBER)
        self.assertEqual(alert.threshold_applied, 1.15)

        # Test on chicane (no per-driver row) -> also the zone's limit (1.30)
        reading_chicane = {
            "recorded_at": (self.now + timedelta(seconds=2)).isoformat(),
            "lateral_g": 1.35,
            "speed_kmh": 60.0,
            "gps_lat": 12.9716,
            "gps_lng": 77.5946,
            "zone": str(self.zone_chicane.id),
        }
        res_chicane = self.client.post(
            f"/api/sessions/{self.session.id}/telemetry/",
            reading_chicane,
            format="json",
        )
        self.assertEqual(res_chicane.status_code, status.HTTP_201_CREATED)

        alert_chicane = Alert.objects.filter(session=self.session, zone=self.zone_chicane).first()
        self.assertIsNotNone(alert_chicane)
        self.assertEqual(alert_chicane.threshold_applied, 1.30)

    def test_device_can_only_write_to_assigned_driver_session(self):
        """A device can only write to its assigned driver's session (other driver -> 403)."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Device-Token {self.raw_token}")

        reading = {
            "recorded_at": (self.now + timedelta(seconds=1)).isoformat(),
            "lateral_g": 0.80,
            "speed_kmh": 60.0,
            "gps_lat": 12.9716,
            "gps_lng": 77.5946,
        }

        # Assigned driver's session -> 201
        ok_res = self.client.post(
            f"/api/sessions/{self.session.id}/telemetry/",
            reading,
            format="json",
        )
        self.assertEqual(ok_res.status_code, status.HTTP_201_CREATED)

        # Other driver's session -> 403
        forbidden_res = self.client.post(
            f"/api/sessions/{self.other_session.id}/telemetry/",
            reading,
            format="json",
        )
        self.assertEqual(forbidden_res.status_code, status.HTTP_403_FORBIDDEN)

    def test_alerts_summary_shows_per_zone_counts(self):
        """After ingestion, the driver's alerts/summary shows the per-zone counts."""
        self.as_kart_unit()

        # Ingest reading that triggers red alert in Hairpin
        self.client.post(
            f"/api/sessions/{self.session.id}/telemetry/",
            {
                "recorded_at": (self.now + timedelta(seconds=1)).isoformat(),
                "lateral_g": 1.25,
                "speed_kmh": 60.0,
                "gps_lat": 12.9716,
                "gps_lng": 77.5946,
                "zone": str(self.zone_hairpin.id),
            },
            format="json",
        )

        # The driver reads their own summary with their own sign-in
        self.client.credentials()
        self.client.force_authenticate(user=self.driver)
        summary_res = self.client.get("/api/sessions/alerts/summary/")
        self.assertEqual(summary_res.status_code, status.HTTP_200_OK)
        data = summary_res.json()
        self.assertTrue(data["has_sessions"])

        zones_map = {z["name"]: z for z in data["zones"]}
        self.assertIn("Hairpin", zones_map)
        self.assertEqual(zones_map["Hairpin"]["count"], 1)
        self.assertEqual(zones_map["Hairpin"]["red_count"], 1)
        self.assertEqual(zones_map["Hairpin"]["status"], "High Risk")
