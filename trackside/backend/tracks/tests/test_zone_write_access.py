"""
Trackside — Every zone write needs Admin (or Admin/Coach), refuses locked tracks and keeps history (P2).

Covers ZoneDetailView (PUT, PATCH, DELETE), the corner editor save, and the limit-history endpoint.
"""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from tracks.models import Track, Zone, ZoneThresholdHistory
from tracks.tests.track_factory import make_imported_track

User = get_user_model()
RANGE = {"start": {"lat": 12.97, "lng": 77.59}, "end": {"lat": 12.9702, "lng": 77.5902}}


class ZoneWriteBase(APITestCase):
    """Users, an editable track, a built-in track and an archived track, each with one zone."""

    def setUp(self):
        """Create the users, tracks and zones."""
        super().setUp()
        make = User.objects.create_user
        self.admin = make(email="zw_admin@trackside.local", name="A", password="AdminPassword123!", role="admin")
        self.coach = make(email="zw_coach@trackside.local", name="C", password="CoachPassword123!", role="coach")
        self.driver = make(email="zw_driver@trackside.local", name="D", password="DriverPassword123!", role="driver")
        self.track = Track.objects.create(name="Write Track", kart_class="sprint")
        self.builtin = Track.objects.create(name="Demo Circuit", is_builtin=True, kart_class="sprint")
        self.archived = Track.objects.create(name="Old Track", is_archived=True, kart_class="sprint")
        self.zones = {t.name: Zone.objects.create(track=t, label="Turn", threshold_g=1.3, gps_range=RANGE)
                      for t in (self.track, self.builtin, self.archived)}

    def url(self, track):
        """The detail URL of the track's zone."""
        return f"/api/tracks/{track.id}/zones/{self.zones[track.name].id}/"


class TestZoneDetailWrites(ZoneWriteBase):
    """PUT, PATCH and DELETE on one zone."""

    def test_only_admin_may_change_or_delete(self):
        """Coach and driver get 403 for PATCH, PUT and DELETE; nothing changes."""
        for user in (self.coach, self.driver):
            self.client.force_authenticate(user)
            self.assertEqual(self.client.patch(self.url(self.track), {"threshold_g": 1.1}, format="json").status_code, 403)
            self.assertEqual(self.client.put(self.url(self.track), {"label": "X"}, format="json").status_code, 403)
            self.assertEqual(self.client.delete(self.url(self.track)).status_code, 403)
        self.client.force_authenticate(None)
        self.assertIn(self.client.patch(self.url(self.track), {"threshold_g": 1.1}, format="json").status_code, (401, 403))
        zone = self.zones["Write Track"]
        zone.refresh_from_db()
        self.assertEqual(zone.threshold_g, 1.3)

    def test_built_in_and_archived_tracks_refuse_every_write(self):
        """Even an Admin gets 409 and the zone is untouched."""
        self.client.force_authenticate(self.admin)
        for track in (self.builtin, self.archived):
            for verb, body in (("patch", {"threshold_g": 1.1}), ("put", {"label": "X", "threshold_g": 1.1, "gps_range": RANGE}), ("delete", None)):
                response = getattr(self.client, verb)(self.url(track), body, format="json") if body else self.client.delete(self.url(track))
                self.assertEqual(response.status_code, 409, f"{track.name} {verb}")
            zone = self.zones[track.name]
            zone.refresh_from_db()
            self.assertEqual((zone.label, zone.threshold_g, zone.is_active), ("Turn", 1.3, True))
        self.assertEqual(ZoneThresholdHistory.objects.count(), 0)

    def test_admin_change_is_checked_and_recorded(self):
        """A good PATCH saves and writes one history row; bad names, limits and gps_range are 400."""
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.patch(self.url(self.track), {"threshold_g": 1.1}, format="json").status_code, 200)
        row = ZoneThresholdHistory.objects.get()
        self.assertEqual((row.old_g, row.new_g, row.changed_by), (1.3, 1.1, self.admin))
        for bad in ({"threshold_g": 0.2}, {"threshold_g": 1.6}, {"label": ""}, {"label": "x" * 41}, {"label": "Straight 2"},
                    {"gps_range": {"start": {"lat": 200, "lng": 0}, "end": RANGE["end"]}}, {"gps_range": "nowhere"}):
            self.assertEqual(self.client.patch(self.url(self.track), bad, format="json").status_code, 400, bad)
        zone = self.zones["Write Track"]
        zone.refresh_from_db()
        self.assertEqual((zone.label, zone.threshold_g), ("Turn", 1.1))
        self.assertEqual(ZoneThresholdHistory.objects.count(), 1)

    def test_a_zone_from_another_track_is_not_reachable_through_this_track(self):
        """Using track A's URL with track B's zone id is a 404 and changes nothing."""
        self.client.force_authenticate(self.admin)
        wrong = f"/api/tracks/{self.track.id}/zones/{self.zones['Old Track'].id}/"
        self.assertEqual(self.client.patch(wrong, {"threshold_g": 1.1}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(wrong).status_code, 404)


class TestEditorAndHistoryWrites(APITestCase):
    """Corner editor save and the limit-history endpoint."""

    def setUp(self):
        """Create a coach, a driver and two imported tracks."""
        super().setUp()
        make = User.objects.create_user
        self.coach = make(email="ew_coach@trackside.local", name="C", password="CoachPassword123!", role="coach")
        self.driver = make(email="ew_driver@trackside.local", name="D", password="DriverPassword123!", role="driver")
        self.track = make_imported_track(self.coach, name="Editor A")
        self.other = make_imported_track(self.coach, name="Editor B")
        self.client.force_authenticate(self.coach)
        self.url = f"/api/tracks/{self.track.id}/corners/"

    def payload(self):
        """The editor payload of track A."""
        return self.client.get(self.url).data

    def test_a_marker_id_from_another_track_cannot_be_used(self):
        """Saving with track B's zone id is a 409 and track B's zone is unchanged."""
        data = self.payload()
        foreign = self.other.zones.first()
        markers = [{k: m[k] for k in ("id", "label", "threshold_g", "center_index", "length_m")} for m in data["markers"]]
        markers[0]["id"] = str(foreign.id)
        markers[0]["label"] = "Hijacked"
        response = self.client.put(self.url, {"outline_version": data["outline_version"], "markers": markers}, format="json")
        self.assertEqual(response.status_code, 409)
        foreign.refresh_from_db()
        self.assertNotEqual(foreign.label, "Hijacked")

    def test_an_inactive_zone_id_cannot_be_revived_by_saving(self):
        """A deactivated corner's id is not accepted again."""
        data = self.payload()
        dead = self.track.zones.first()
        Zone.objects.filter(pk=dead.pk).update(is_active=False)
        markers = [{k: m[k] for k in ("id", "label", "threshold_g", "center_index", "length_m")} for m in data["markers"]]
        response = self.client.put(self.url, {"outline_version": data["outline_version"], "markers": markers}, format="json")
        self.assertEqual(response.status_code, 409)

    def test_only_admin_and_coach_may_save_and_a_limit_change_is_recorded(self):
        """A driver gets 403; a coach's limit change adds a history row."""
        data = self.payload()
        markers = [{k: m[k] for k in ("id", "label", "threshold_g", "center_index", "length_m")} for m in data["markers"]]
        self.client.force_authenticate(self.driver)
        self.assertEqual(self.client.put(self.url, {"outline_version": data["outline_version"], "markers": markers}, format="json").status_code, 403)
        self.client.force_authenticate(self.coach)
        markers[0]["threshold_g"] = 1.05
        self.assertEqual(self.client.put(self.url, {"outline_version": data["outline_version"], "markers": markers}, format="json").status_code, 200)
        zone = Zone.objects.get(pk=markers[0]["id"])
        self.assertTrue(ZoneThresholdHistory.objects.filter(zone=zone, old_g=1.2, new_g=1.05, changed_by=self.coach).exists())

    def test_zones_made_by_import_and_editor_start_their_history_at_creation(self):
        """Every imported corner has an initial row; a corner added in the editor gets one too."""
        for zone in self.track.zones.all():
            self.assertEqual(ZoneThresholdHistory.objects.filter(zone=zone, old_g=zone.threshold_g, new_g=zone.threshold_g).count(), 1)
        data = self.payload()
        markers = [{k: m[k] for k in ("id", "label", "threshold_g", "center_index", "length_m")} for m in data["markers"]]
        markers.append({"id": None, "label": "Added", "threshold_g": 1.3, "center_index": 20, "length_m": 20})
        self.client.put(self.url, {"outline_version": data["outline_version"], "markers": markers}, format="json")
        added = Zone.objects.get(track=self.track, label="Added")
        self.assertEqual(ZoneThresholdHistory.objects.filter(zone=added).count(), 1)

    def test_history_endpoint_has_no_write_verbs_and_checks_the_track(self):
        """POST, PUT, PATCH, DELETE are 405; asking through the wrong track shows nothing."""
        zone = self.track.zones.first()
        url = f"/api/tracks/{self.track.id}/zones/{zone.id}/limit-history/"
        for verb in (self.client.post, self.client.put, self.client.patch, self.client.delete):
            self.assertEqual(verb(url, {}, format="json").status_code, 405)
        wrong = f"/api/tracks/{self.other.id}/zones/{zone.id}/limit-history/"
        self.assertEqual(self.client.get(wrong).data["results"], [])
