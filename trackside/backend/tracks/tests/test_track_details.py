"""
Trackside — Tests for map details (rename, kart class), session_count and corner types.
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from driving_sessions.models import Session
from tracks.models import Track, Zone
from tracks.tests.test_corner_editor import api_markers
from tracks.tests.track_factory import make_imported_track

User = get_user_model()


class TestTrackDetails(APITestCase):
    """PATCH renames a map (Admin only), validates the name and the kart class change."""

    def setUp(self):
        """Create the users and tracks this test class needs."""
        super().setUp()
        make = User.objects.create_user
        self.admin = make(email="det_admin@trackside.local", name="A", password="AdminPassword123!", role="admin")
        self.coach = make(email="det_coach@trackside.local", name="C", password="CoachPassword123!", role="coach")
        self.track = Track.objects.create(name="First Track", kart_class=Track.KartClass.SPRINT)
        Track.objects.create(name="Taken Name", is_archived=True)
        self.url = f"/api/tracks/{self.track.id}/"
        self.client.force_authenticate(self.admin)

    def patch(self, body, user=None):
        """PATCH the track as the given user (admin by default)."""
        self.client.force_authenticate(user or self.admin)
        return self.client.patch(self.url, body, format="json")

    def test_admin_renames_and_name_is_trimmed(self):
        """200 and the stored name is cleaned of extra spaces."""
        response = self.patch({"name": "  Kari   Speedway "})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Track.objects.get(pk=self.track.pk).name, "Kari Speedway")

    def test_coach_cannot_rename(self):
        """403 for a coach; the name is unchanged."""
        self.assertEqual(self.patch({"name": "Nope"}, self.coach).status_code, 403)
        self.assertEqual(Track.objects.get(pk=self.track.pk).name, "First Track")

    def test_blank_duplicate_and_too_long_names_are_400(self):
        """Blank, a name used by another map (archived too, any case) and 151 characters are refused."""
        for name in ("   ", "taken name", "x" * 151):
            self.assertEqual(self.patch({"name": name}).status_code, 400, name)
        self.assertEqual(Track.objects.get(pk=self.track.pk).name, "First Track")

    def test_keeping_the_same_name_is_fine(self):
        """Saving a map under its own name (other case) is not a clash."""
        self.assertEqual(self.patch({"name": "FIRST TRACK"}).status_code, 200)

    def test_kart_class_change_refused_when_a_limit_would_not_fit(self):
        """Sprint to rental with a 1.2 g corner is 400 naming the corner; with a 0.7 g corner it works."""
        zone = Zone.objects.create(track=self.track, label="Hairpin", threshold_g=1.2)
        response = self.patch({"kart_class": "rental"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Hairpin", str(response.data))
        self.assertEqual(Track.objects.get(pk=self.track.pk).kart_class, "sprint")
        zone.threshold_g = 0.7
        zone.save()
        self.assertEqual(self.patch({"kart_class": "rental"}).status_code, 200)

    def test_session_count_is_listed_and_in_detail(self):
        """session_count is 0 for an unused map and counts sessions for a used one, in list and detail."""
        self.assertEqual(self.client.get(self.url).data["session_count"], 0)
        Session.objects.create(driver=self.coach, track=self.track, started_at=timezone.now())
        Session.objects.create(driver=self.coach, track=self.track, started_at=timezone.now())
        self.assertEqual(self.client.get(self.url).data["session_count"], 2)
        rows = {t["name"]: t["session_count"] for t in self.client.get("/api/tracks/").data["results"]}
        self.assertEqual(rows["First Track"], 2)


class TestCornerTypes(APITestCase):
    """The corner editor can read and save the corner type."""

    def setUp(self):
        """Create a coach and an imported track with corners."""
        super().setUp()
        self.coach = User.objects.create_user(email="ct_coach@trackside.local", name="C", password="CoachPassword123!", role="coach")
        self.track = make_imported_track(self.coach, name="Type Track", limit=1.2)
        self.client.force_authenticate(self.coach)
        self.url = f"/api/tracks/{self.track.id}/corners/"

    def test_markers_carry_their_type_and_it_can_be_changed(self):
        """GET shows the type; PUT with corner_type saves it; PUT without keeps it."""
        payload = self.client.get(self.url).data
        self.assertTrue(all("corner_type" in m for m in payload["markers"]))
        markers = api_markers(payload)
        markers[0]["corner_type"] = "hairpin"
        body = {"outline_version": payload["outline_version"], "markers": markers}
        saved = self.client.put(self.url, body, format="json")
        self.assertEqual(saved.status_code, 200, saved.data)
        self.assertEqual(Zone.objects.get(pk=markers[0]["id"]).corner_type, "hairpin")
        for m in markers:
            m.pop("corner_type", None)
        self.client.put(self.url, {"outline_version": payload["outline_version"], "markers": markers}, format="json")
        self.assertEqual(Zone.objects.get(pk=markers[0]["id"]).corner_type, "hairpin")

    def test_unknown_type_is_400_and_saves_nothing(self):
        """A made-up type gives a clear message."""
        payload = self.client.get(self.url).data
        markers = api_markers(payload)
        markers[0]["corner_type"] = "loop-the-loop"
        response = self.client.put(self.url, {"outline_version": payload["outline_version"], "markers": markers}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("corner type", response.data["detail"])
