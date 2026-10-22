"""
Trackside — Who may add a zone (corner), and what a new zone must look like (P1).

POST /api/tracks/<id>/zones/ used to accept any signed-in user, so a driver could change
which corners raise alerts. Now it is Admin and Coach only, refuses locked tracks, and
checks name, limit and gps_range.
"""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from tracks.models import Track, Zone, ZoneThresholdHistory

User = get_user_model()
GOOD_RANGE = {"start": {"lat": 12.97, "lng": 77.59}, "end": {"lat": 12.9702, "lng": 77.5902}}


def zone_body(**change):
    """A valid zone request body, with optional changes."""
    body = {"label": "New Corner", "corner_type": "other", "threshold_g": 1.2, "gps_range": GOOD_RANGE}
    body.update(change)
    return body


class ZoneCreateBase(APITestCase):
    """Users and a custom, a built-in and an archived track."""

    def setUp(self):
        """Create one user per role and the three kinds of track."""
        super().setUp()
        make = User.objects.create_user
        self.admin = make(email="zc_admin@trackside.local", name="A", password="AdminPassword123!", role="admin")
        self.coach = make(email="zc_coach@trackside.local", name="C", password="CoachPassword123!", role="coach")
        self.driver = make(email="zc_driver@trackside.local", name="D", password="DriverPassword123!", role="driver")
        self.track = Track.objects.create(name="Zone Track", kart_class="sprint")
        self.builtin = Track.objects.create(name="Demo Circuit", is_builtin=True, kart_class="sprint")
        self.archived = Track.objects.create(name="Old Track", is_archived=True, kart_class="sprint")

    def post(self, track=None, user=None, **change):
        """POST a zone as the given user (coach by default) to the given track."""
        self.client.force_authenticate(user or self.coach)
        return self.client.post(f"/api/tracks/{(track or self.track).id}/zones/", zone_body(**change), format="json")


class TestWhoMayCreate(ZoneCreateBase):
    """Role checks."""

    def test_admin_and_coach_can_create(self):
        """Both allowed roles get 201 and the zone is saved on the track."""
        for index, user in enumerate((self.admin, self.coach)):
            response = self.post(user=user, label=f"Corner {index}")
            self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self.track.zones.count(), 2)

    def test_driver_and_anonymous_are_refused_and_nothing_is_saved(self):
        """A driver gets 403, logged-out callers 401/403; no zone appears."""
        self.assertEqual(self.post(user=self.driver).status_code, 403)
        self.client.force_authenticate(None)
        response = self.client.post(f"/api/tracks/{self.track.id}/zones/", zone_body(), format="json")
        self.assertIn(response.status_code, (401, 403))
        self.assertEqual(Zone.objects.count(), 0)

    def test_everyone_signed_in_can_still_read_zones(self):
        """GET stays open to drivers."""
        Zone.objects.create(track=self.track, label="Read Me", threshold_g=1.2, gps_range=GOOD_RANGE)
        self.client.force_authenticate(self.driver)
        self.assertEqual(self.client.get(f"/api/tracks/{self.track.id}/zones/").status_code, 200)

    def test_unknown_track_is_404(self):
        """A coach posting to a track that does not exist gets 404."""
        self.client.force_authenticate(self.coach)
        response = self.client.post("/api/tracks/00000000-0000-0000-0000-000000000000/zones/", zone_body(), format="json")
        self.assertEqual(response.status_code, 404)


class TestLockedTracks(ZoneCreateBase):
    """Built-in and archived tracks refuse new zones."""

    def test_built_in_track_is_409_with_the_lock_message(self):
        """Even an Admin cannot add a corner to the Demo Circuit."""
        response = self.post(track=self.builtin, user=self.admin)
        self.assertEqual(response.status_code, 409)
        self.assertIn("Demo Circuit is locked", response.data["detail"])
        self.assertEqual(self.builtin.zones.count(), 0)

    def test_archived_track_is_409(self):
        """An archived map says to restore it first."""
        response = self.post(track=self.archived)
        self.assertEqual(response.status_code, 409)
        self.assertIn("archived", response.data["detail"])
        self.assertEqual(self.archived.zones.count(), 0)

    def test_lock_is_checked_before_the_data(self):
        """Bad data on a locked track is still the 409, not a 400."""
        self.assertEqual(self.post(track=self.builtin, label="").status_code, 409)


class TestZoneChecks(ZoneCreateBase):
    """Name, limit and gps_range."""

    def test_bad_names_are_400(self):
        """Missing, blank, 41 characters, control character and 'Straight...' names are refused."""
        for label in ("", "   ", "x" * 41, "a\x00b", "Straight", "straightaway"):
            self.assertEqual(self.post(label=label).status_code, 400, repr(label))
        self.client.force_authenticate(self.coach)
        body = zone_body()
        del body["label"]
        self.assertEqual(self.client.post(f"/api/tracks/{self.track.id}/zones/", body, format="json").status_code, 400)

    def test_name_boundary_and_trimming(self):
        """40 characters is fine and spaces around a name are removed."""
        self.assertEqual(self.post(label="n" * 40).status_code, 201)
        response = self.post(label="  Padded  ")
        self.assertEqual(response.data["label"], "Padded")

    def test_limit_must_be_inside_the_tracks_range(self):
        """0.3 and 1.5 are fine on a sprint track; 0.29, 1.51, text and NaN are refused."""
        for limit in (0.29, 1.51, 5, "abc", None):
            self.assertEqual(self.post(label=f"L{limit}", threshold_g=limit).status_code, 400, repr(limit))
        self.assertEqual(self.post(label="Low", threshold_g=1.0).status_code, 201)
        self.assertEqual(self.post(label="High", threshold_g=1.5).status_code, 201)

    def test_gps_range_is_required_and_must_be_valid(self):
        """Missing, wrong shape, out-of-range, NaN-like and unknown-key gps_range values are refused."""
        bad_ranges = [
            None, {}, "x", [], {"start": GOOD_RANGE["start"]}, {"end": GOOD_RANGE["end"]},
            {"start": {"lat": 91, "lng": 0}, "end": GOOD_RANGE["end"]},
            {"start": {"lat": 0, "lng": 181}, "end": GOOD_RANGE["end"]},
            {"start": {"lat": "12", "lng": 77}, "end": GOOD_RANGE["end"]},
            {"start": {"lat": True, "lng": 77}, "end": GOOD_RANGE["end"]},
            {"start": {"lat": 1, "lng": 2, "extra": 3}, "end": GOOD_RANGE["end"]},
            dict(GOOD_RANGE, surprise=1), dict(GOOD_RANGE, length_m=-5), dict(GOOD_RANGE, center={"lat": 99, "lng": 0}),
        ]
        for index, value in enumerate(bad_ranges):
            self.assertEqual(self.post(label=f"G{index}", gps_range=value).status_code, 400, repr(value))
        self.client.force_authenticate(self.coach)
        body = zone_body()
        del body["gps_range"]
        self.assertEqual(self.client.post(f"/api/tracks/{self.track.id}/zones/", body, format="json").status_code, 400)
        full = dict(GOOD_RANGE, center={"lat": 12.9701, "lng": 77.5901}, length_m=30)
        self.assertEqual(self.post(label="Full", gps_range=full).status_code, 201)

    def test_first_history_row_is_written_on_creation(self):
        """A new zone starts its limit history with one row (old and new limit equal)."""
        response = self.post(threshold_g=1.3)
        rows = ZoneThresholdHistory.objects.filter(zone_id=response.data["id"])
        self.assertEqual(rows.count(), 1)
        row = rows.get()
        self.assertEqual((row.old_g, row.new_g, row.changed_by), (1.3, 1.3, self.coach))

    def test_failed_create_writes_no_history(self):
        """A refused request leaves no zone and no history behind."""
        self.post(threshold_g=9)
        self.assertEqual(ZoneThresholdHistory.objects.count(), 0)
