"""
Trackside — Tests for GET /api/sessions/<id>/corner-deltas/ (K1).

Readings are 0.5 s apart, so the reading interval is 0.5 s and every number below is hand-worked.
"""

from datetime import datetime, timedelta, timezone

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from driving_sessions.models import Session, Telemetry
from tracks.models import Track, Zone

User = get_user_model()
START = datetime(2026, 10, 16, 10, 0, 0, tzinfo=timezone.utc)


class CornerDeltasBase(APITestCase):
    """A track with two corners and a session whose readings are built from (lap, corner) pairs."""

    def setUp(self):
        """Create users, a track with Turn Z (met first) and Turn A (met second), and one open session."""
        super().setUp()
        make = lambda e, r: User.objects.create_user(email=e, name=e, password="Passw0rd!12345", role=r)
        self.coach, self.driver, self.other = make("cd_coach@t.local", "coach"), make("cd_driver@t.local", "driver"), make("cd_other@t.local", "driver")
        self.track = Track.objects.create(name="Delta Circuit", kart_class=Track.KartClass.SPRINT)
        self.zone_z = Zone.objects.create(track=self.track, label="Turn Z", threshold_g=1.2, gps_range={})
        self.zone_a = Zone.objects.create(track=self.track, label="Turn A", threshold_g=1.2, gps_range={})
        self.session = Session.objects.create(driver=self.driver, track=self.track, mode=Session.Mode.SAFETY,
                                              kart_number="7", started_at=START)

    def add(self, pairs, session=None):
        """Store one reading every 0.5 s for each (lap, zone-or-None) pair, in order."""
        Telemetry.objects.bulk_create([
            Telemetry(session=session or self.session, zone=zone, recorded_at=START + timedelta(seconds=0.5 * i),
                      lateral_g=1.0, speed_kmh=50.0, gps_lat=10.0, gps_lng=76.0, lap_number=lap)
            for i, (lap, zone) in enumerate(pairs)])

    def get(self, user, session_id=None):
        """GET the endpoint signed in as user."""
        self.client.force_authenticate(user=user)
        return self.client.get(f"/api/sessions/{session_id or self.session.id}/corner-deltas/")

    def corner(self, response, label):
        """The entry for one corner label."""
        return next(c for c in response.json()["corners"] if c["label"] == label)

    def three_laps(self):
        """Lap 1: Z x3, A x2. Lap 2: Z x4, A x3. Lap 3 (in progress): Z x2."""
        z, a = self.zone_z, self.zone_a
        self.add([(1, z)] * 3 + [(1, a)] * 2 + [(2, z)] * 4 + [(2, a)] * 3 + [(3, z)] * 2)


class TestCornerDeltaNumbers(CornerDeltasBase):
    """Times, bests and deltas."""

    def test_times_best_and_deltas_use_only_completed_laps(self):
        """Z: lap1 1.5, lap2 2.0, current lap3 1.0 (shown, never best). Best 1.5, last lap 2.0 (+0.5)."""
        self.three_laps()
        z = self.corner(self.get(self.coach), "Turn Z")
        self.assertEqual((z["best_s"], z["last_lap_s"], z["last_lap_delta_s"]), (1.5, 2.0, 0.5))
        self.assertEqual([(l["lap_number"], l["time_s"], l["delta_s"], l["completed"]) for l in z["laps"]],
                         [(1, 1.5, 0.0, True), (2, 2.0, 0.5, True), (3, 1.0, -0.5, False)])

    def test_corners_are_listed_in_the_order_the_kart_meets_them(self):
        """Turn Z comes before Turn A although A sorts first by name."""
        self.three_laps()
        self.assertEqual([c["label"] for c in self.get(self.coach).json()["corners"]], ["Turn Z", "Turn A"])

    def test_corner_not_yet_driven_in_current_lap_has_no_entry_for_it(self):
        """Turn A has two completed laps only: 1.0 and 1.5, best 1.0, last lap +0.5."""
        self.three_laps()
        a = self.corner(self.get(self.coach), "Turn A")
        self.assertEqual((a["best_s"], a["last_lap_s"], a["last_lap_delta_s"], len(a["laps"])), (1.0, 1.5, 0.5, 2))

    def test_one_completed_lap_gives_null_deltas_not_zeros(self):
        """With a single completed lap the best is known but every delta is null."""
        self.add([(1, self.zone_z)] * 3 + [(2, self.zone_z)] * 2)
        z = self.corner(self.get(self.coach), "Turn Z")
        self.assertEqual((z["best_s"], z["last_lap_s"], z["last_lap_delta_s"]), (1.5, 1.5, None))
        self.assertEqual([l["delta_s"] for l in z["laps"]], [None, None])

    def test_ended_session_counts_its_last_lap_as_completed(self):
        """Once ended_at is set the current lap is completed too, so it can be the best."""
        self.three_laps()
        Session.objects.filter(pk=self.session.pk).update(ended_at=START + timedelta(minutes=5))
        z = self.corner(self.get(self.coach), "Turn Z")
        self.assertEqual((z["best_s"], z["last_lap_s"], z["last_lap_delta_s"]), (1.0, 1.0, 0.0))

    def test_no_readings_gives_null_numbers_and_inactive_corners_are_left_out(self):
        """Every active corner appears with null values; a retired corner does not."""
        Zone.objects.filter(pk=self.zone_a.pk).update(is_active=False)
        response = self.get(self.coach)
        self.assertEqual([c["label"] for c in response.json()["corners"]], ["Turn Z"])
        z = self.corner(response, "Turn Z")
        self.assertEqual((z["best_s"], z["last_lap_s"], z["last_lap_delta_s"], z["laps"]), (None, None, None, []))


class TestCornerDeltaAccess(CornerDeltasBase):
    """Who may read it, and that a hidden session looks exactly like a missing one."""

    def test_coach_any_driver_own_only(self):
        """Coach and the session's driver get 200; another driver gets 404."""
        self.assertEqual(self.get(self.coach).status_code, 200)
        self.assertEqual(self.get(self.driver).status_code, 200)
        self.assertEqual(self.get(self.other).status_code, 404)

    def test_hidden_and_missing_sessions_answer_identically(self):
        """Same status and same body for another driver's session and a made-up id."""
        hidden = self.get(self.other)
        missing = self.get(self.other, "11111111-2222-3333-4444-555555555555")
        self.assertEqual((hidden.status_code, hidden.json()), (missing.status_code, missing.json()))

    def test_signed_out_is_refused(self):
        """No login, no data."""
        self.client.force_authenticate(user=None)
        self.assertIn(self.client.get(f"/api/sessions/{self.session.id}/corner-deltas/").status_code, (401, 403))
