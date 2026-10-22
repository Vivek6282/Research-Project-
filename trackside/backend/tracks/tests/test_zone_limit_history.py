"""
Trackside — Tests for Zone.is_active, zone retirement and the insert-only limit history (H3 data).
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from driving_sessions.models import Alert, Session, Telemetry
from tracks.limit_history import set_zone_limit
from tracks.models import Track, Zone, ZoneThresholdHistory
from tracks.zone_retirement import DEACTIVATED, DELETED, retire_zone

User = get_user_model()


class TestZoneLimitHistory(APITestCase):
    """History rows are written on change, never edited, and never deleted."""

    def setUp(self):
        """Create an admin, a coach, a track and a zone."""
        super().setUp()
        make = User.objects.create_user
        self.admin = make(email="zh_admin@trackside.local", name="Admin", password="AdminPassword123!", role="admin")
        self.coach = make(email="zh_coach@trackside.local", name="Coach", password="CoachPassword123!", role="coach")
        self.track = Track.objects.create(name="History Track", kart_class="sprint")
        self.zone = Zone.objects.create(track=self.track, label="Turn A", threshold_g=1.3)

    def test_changing_a_limit_adds_one_history_row(self):
        """Old and new limit and the person are recorded; the zone holds the new limit."""
        self.assertTrue(set_zone_limit(self.zone, 1.1, self.coach))
        row = ZoneThresholdHistory.objects.get()
        self.assertEqual((row.old_g, row.new_g, row.changed_by), (1.3, 1.1, self.coach))
        self.zone.refresh_from_db()
        self.assertEqual(self.zone.threshold_g, 1.1)

    def test_same_limit_adds_nothing(self):
        """No change, no row."""
        self.assertFalse(set_zone_limit(self.zone, 1.3, self.coach))
        self.assertEqual(ZoneThresholdHistory.objects.count(), 0)

    def test_history_rows_cannot_be_updated_or_deleted(self):
        """Saving an existing row, deleting it, or bulk update/delete all raise."""
        set_zone_limit(self.zone, 1.2, self.coach)
        row = ZoneThresholdHistory.objects.get()
        row.new_g = 1.4
        with self.assertRaises(ValueError):
            row.save()
        with self.assertRaises(ValueError):
            row.delete()
        with self.assertRaises(ValueError):
            ZoneThresholdHistory.objects.all().update(new_g=1.5)
        with self.assertRaises(ValueError):
            ZoneThresholdHistory.objects.all().delete()
        self.assertEqual(ZoneThresholdHistory.objects.get().new_g, 1.2)

    def test_admin_patch_of_a_zone_limit_is_recorded(self):
        """The existing zone PATCH endpoint now writes history."""
        self.client.force_authenticate(self.admin)
        response = self.client.patch(f"/api/tracks/{self.track.id}/zones/{self.zone.id}/", {"threshold_g": 1.25}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(ZoneThresholdHistory.objects.filter(zone=self.zone, new_g=1.25).count(), 1)

    def test_history_endpoint_is_read_only_and_staff_only(self):
        """Coach can read it; drivers cannot; there is no write verb."""
        set_zone_limit(self.zone, 1.2, self.coach)
        url = f"/api/tracks/{self.track.id}/zones/{self.zone.id}/limit-history/"
        self.client.force_authenticate(self.coach)
        self.assertEqual(self.client.get(url).data["results"][0]["new_g"], 1.2)
        for verb in (self.client.post, self.client.put, self.client.patch, self.client.delete):
            self.assertEqual(verb(url, {}, format="json").status_code, 405)
        driver = User.objects.create_user(email="zh_driver@trackside.local", name="D", password="DriverPassword123!", role="driver")
        self.client.force_authenticate(driver)
        self.assertEqual(self.client.get(url).status_code, 403)


class TestZoneRetirement(APITestCase):
    """A corner with history is deactivated; one without is deleted."""

    def setUp(self):
        """Create a driver, a track and a session."""
        super().setUp()
        self.driver = User.objects.create_user(
            email="zr_driver@trackside.local", name="D", password="DriverPassword123!", role="driver")
        self.track = Track.objects.create(name="Retire Track")
        self.session = Session.objects.create(driver=self.driver, track=self.track, started_at=timezone.now())

    def test_zone_without_history_is_deleted(self):
        """No telemetry, alerts, notes or limits: it is removed."""
        zone = Zone.objects.create(track=self.track, label="Empty", threshold_g=1.2)
        self.assertEqual(retire_zone(zone), DELETED)
        self.assertFalse(Zone.objects.filter(pk=zone.pk).exists())

    def test_zone_with_telemetry_is_deactivated_and_hidden(self):
        """Telemetry keeps the zone; it disappears from the track and zone lists."""
        zone = Zone.objects.create(track=self.track, label="Used", threshold_g=1.2)
        Telemetry.objects.create(session=self.session, zone=zone, lateral_g=1.0, speed_kmh=50, gps_lat=0.0, gps_lng=0.0, recorded_at=timezone.now())
        self.assertEqual(retire_zone(zone), DEACTIVATED)
        zone.refresh_from_db()
        self.assertFalse(zone.is_active)
        self.client.force_authenticate(self.driver)
        self.assertEqual(self.client.get(f"/api/tracks/{self.track.id}/").data["zones"], [])
        self.assertEqual(self.client.get(f"/api/tracks/{self.track.id}/zones/").data["results"], [])

    def test_zone_with_alerts_survives_and_keeps_its_alerts(self):
        """Alerts are cascade-deleted with a zone, so a zone with alerts must be kept."""
        zone = Zone.objects.create(track=self.track, label="Alerted", threshold_g=1.2)
        Alert.objects.create(session=self.session, zone=zone, severity="red", g_value=1.4, threshold_applied=1.2, triggered_at=timezone.now())
        self.assertEqual(retire_zone(zone), DEACTIVATED)
        self.assertEqual(Alert.objects.filter(zone=zone).count(), 1)

    def test_admin_zone_delete_endpoint_uses_the_same_rule(self):
        """DELETE on a zone with history answers 200 'deactivated'; without history 204."""
        admin = User.objects.create_user(email="zr_admin@trackside.local", name="A", password="AdminPassword123!", role="admin")
        self.client.force_authenticate(admin)
        used = Zone.objects.create(track=self.track, label="Used", threshold_g=1.2)
        Telemetry.objects.create(session=self.session, zone=used, lateral_g=1.0, speed_kmh=50, gps_lat=0.0, gps_lng=0.0, recorded_at=timezone.now())
        response = self.client.delete(f"/api/tracks/{self.track.id}/zones/{used.id}/")
        self.assertEqual((response.status_code, response.data["status"]), (200, "deactivated"))
        empty = Zone.objects.create(track=self.track, label="Empty", threshold_g=1.2)
        self.assertEqual(self.client.delete(f"/api/tracks/{self.track.id}/zones/{empty.id}/").status_code, 204)


class TestDemoCircuitEndpoint(APITestCase):
    """POST /api/tracks/demo-circuit/ makes sure the built-in map exists."""

    def setUp(self):
        """Create a coach and a driver."""
        super().setUp()
        make = User.objects.create_user
        self.coach = make(email="dc_coach@trackside.local", name="C", password="CoachPassword123!", role="coach")
        self.driver = make(email="dc_driver@trackside.local", name="D", password="DriverPassword123!", role="driver")

    def test_creates_the_demo_circuit_with_three_corners_once(self):
        """First call creates it locked with Hairpin, Sweeper and Chicane; repeat calls change nothing."""
        self.client.force_authenticate(self.coach)
        first = self.client.post("/api/tracks/demo-circuit/")
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.data["is_builtin"])
        self.assertTrue(first.data["is_schematic"])
        self.assertEqual(sorted(z["label"] for z in first.data["zones"]), ["Chicane", "Hairpin", "Sweeper"])
        Zone.objects.filter(label="Hairpin").update(threshold_g=1.05)
        self.client.post("/api/tracks/demo-circuit/")
        self.assertEqual(Track.objects.filter(name="Demo Circuit").count(), 1)
        self.assertEqual(Zone.objects.get(label="Hairpin").threshold_g, 1.05)

    def test_drivers_cannot_call_it(self):
        """Only Admin and Coach."""
        self.client.force_authenticate(self.driver)
        self.assertEqual(self.client.post("/api/tracks/demo-circuit/").status_code, 403)


class TestDemoCircuitIsNotDuplicated(APITestCase):
    """Calling ensure_demo_circuit again and again never makes a second Demo Circuit or duplicate corners."""

    def test_repeated_calls_keep_one_track_and_three_zones(self):
        """Ten calls: one built-in track, one Hairpin, one Sweeper, one Chicane."""
        from tracks.demo_circuit_setup import ensure_demo_circuit
        for _ in range(10):
            ensure_demo_circuit()
        self.assertEqual(Track.objects.filter(name="Demo Circuit").count(), 1)
        self.assertEqual(Zone.objects.filter(track__name="Demo Circuit").count(), 3)

    def test_an_existing_demo_circuit_is_reused_and_locked(self):
        """A hand-made track called Demo Circuit becomes the locked built-in; no second one appears."""
        from tracks.demo_circuit_setup import ensure_demo_circuit
        Track.objects.create(name="Demo Circuit")
        track = ensure_demo_circuit()
        self.assertTrue(track.is_builtin)
        self.assertEqual(Track.objects.filter(name="Demo Circuit").count(), 1)
