"""
Trackside — Tests for archive instead of delete, restore, and the built-in lock (C7).
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from drivers.models import DriverZoneThreshold
from driving_sessions.models import Session
from tracks.models import Track, Zone

User = get_user_model()


class TestTrackArchive(APITestCase):
    """DELETE archives a used track, deletes an unused one, and never touches the built-in."""

    def setUp(self):
        """Create the users and data this test class needs."""
        super().setUp()
        make = User.objects.create_user
        self.admin = make(email="arch_admin@trackside.local", name="A", password="AdminPassword123!", role="admin")
        self.coach = make(email="arch_coach@trackside.local", name="C", password="CoachPassword123!", role="coach")
        self.driver = make(email="arch_driver@trackside.local", name="D", password="DriverPassword123!", role="driver")
        self.builtin = Track.objects.create(name="Demo Circuit", is_builtin=True, source="builtin")
        self.used = Track.objects.create(name="Used Track")
        self.used_zone = Zone.objects.create(track=self.used, label="Z1", threshold_g=1.2)
        Session.objects.create(driver=self.driver, track=self.used, started_at=timezone.now())
        self.unused = Track.objects.create(name="Unused Track")
        Zone.objects.create(track=self.unused, label="Z1", threshold_g=1.2)

    def delete(self, track, user):
        """DELETE a track as the given user."""
        self.client.force_authenticate(user)
        return self.client.delete(f"/api/tracks/{track.id}/")

    def test_track_with_a_session_is_archived_and_history_kept(self):
        """200 'archived'; the track, its zones and the session all still exist."""
        response = self.delete(self.used, self.coach)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "archived")
        self.used.refresh_from_db()
        self.assertTrue(self.used.is_archived)
        self.assertEqual(Session.objects.filter(track=self.used).count(), 1)
        self.assertEqual(self.used.zones.count(), 1)

    def test_track_with_only_driver_thresholds_is_also_archived(self):
        """Driver threshold history counts as history, so the track is archived, not deleted."""
        zone = self.unused.zones.get()
        DriverZoneThreshold.objects.create(driver=self.driver, zone=zone, custom_threshold_g=1.1, set_by=self.coach)
        self.assertEqual(self.delete(self.unused, self.admin).status_code, 200)
        self.assertTrue(Track.objects.get(pk=self.unused.pk).is_archived)

    def test_never_used_track_is_really_deleted(self):
        """204 and the row and its zones are gone."""
        response = self.delete(self.unused, self.admin)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Track.objects.filter(pk=self.unused.pk).exists())
        self.assertFalse(Zone.objects.filter(track_id=self.unused.pk).exists())

    def test_builtin_track_cannot_be_deleted_archived_or_edited(self):
        """409 with a clear message for DELETE, PATCH, PUT and restore; nothing changes."""
        response = self.delete(self.builtin, self.admin)
        self.assertEqual(response.status_code, 409)
        self.assertIn("Demo Circuit is locked", response.data["detail"])
        self.client.force_authenticate(self.admin)
        url = f"/api/tracks/{self.builtin.id}/"
        self.assertEqual(self.client.patch(url, {"name": "Hacked"}, format="json").status_code, 409)
        self.assertEqual(self.client.put(url, {"name": "Hacked"}, format="json").status_code, 409)
        self.assertEqual(self.client.post(url + "restore/").status_code, 409)
        self.builtin.refresh_from_db()
        self.assertEqual((self.builtin.name, self.builtin.is_archived), ("Demo Circuit", False))

    def test_driver_cannot_archive_delete_or_restore(self):
        """Drivers get 403 on DELETE and restore."""
        self.assertEqual(self.delete(self.used, self.driver).status_code, 403)
        self.client.force_authenticate(self.driver)
        self.assertEqual(self.client.post(f"/api/tracks/{self.used.id}/restore/").status_code, 403)
        self.assertTrue(Track.objects.filter(pk=self.used.pk, is_archived=False).exists())

    def test_coach_cannot_edit_a_track_but_admin_can(self):
        """PATCH stays Admin-only (unchanged); admin can rename a normal track."""
        self.client.force_authenticate(self.coach)
        self.assertEqual(self.client.patch(f"/api/tracks/{self.used.id}/", {"name": "X"}, format="json").status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.patch(f"/api/tracks/{self.used.id}/", {"name": "Renamed"}, format="json").status_code, 200)

    def test_archived_tracks_are_hidden_from_the_default_list_only(self):
        """Default list hides them; ?archived=only and ?archived=all show them."""
        self.delete(self.used, self.coach)
        self.client.force_authenticate(self.driver)

        def names(query=""):
            """Track names returned by the list endpoint."""
            return {t["name"] for t in self.client.get("/api/tracks/" + query).data["results"]}

        self.assertEqual(names(), {"Demo Circuit", "Unused Track"})
        self.assertEqual(names("?archived=only"), {"Used Track"})
        self.assertEqual(names("?archived=all"), {"Demo Circuit", "Used Track", "Unused Track"})

    def test_archived_track_can_still_be_read_for_history(self):
        """GET by id and reference-line keep working for an archived track."""
        self.delete(self.used, self.coach)
        self.client.force_authenticate(self.driver)
        self.assertEqual(self.client.get(f"/api/tracks/{self.used.id}/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/tracks/{self.used.id}/reference-line/").status_code, 200)

    def test_restore_brings_a_track_back(self):
        """Restore clears the flag; restoring an active track is a 400."""
        self.delete(self.used, self.coach)
        self.client.force_authenticate(self.coach)
        response = self.client.post(f"/api/tracks/{self.used.id}/restore/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_archived"])
        self.assertEqual(self.client.post(f"/api/tracks/{self.used.id}/restore/").status_code, 400)

    def test_restore_unknown_track_is_404(self):
        """Unknown id gives 404."""
        self.client.force_authenticate(self.coach)
        self.assertEqual(self.client.post("/api/tracks/00000000-0000-0000-0000-000000000000/restore/").status_code, 404)
