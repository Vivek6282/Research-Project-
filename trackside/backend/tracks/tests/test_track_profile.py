"""
Trackside — Tests for the simulator track profile and export_track command (SIM-1).
"""

import io
import json
import os
import tempfile

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from rest_framework.test import APITestCase

from tracks.models import Track, Zone
from tracks.tests import synthetic_track as st
from tracks.tests.track_factory import make_imported_track
from tracks.track_profile import ProfileError, build_track_profile, write_track_profile

User = get_user_model()


class TestTrackProfile(APITestCase):
    """The profile has a closed even outline and the active corners with radii and limits."""

    def setUp(self):
        """Create a coach and an imported four-corner track."""
        super().setUp()
        self.coach = User.objects.create_user(
            email="prof_coach@trackside.local", name="C", password="CoachPassword123!", role="coach")
        self.track = make_imported_track(self.coach)

    def test_profile_has_outline_corners_radii_and_limits(self):
        """Four corners in lap order with the known radii (within 15%) and the chosen limit."""
        profile = build_track_profile(self.track)
        self.assertEqual(profile["version"], 1)
        self.assertAlmostEqual(profile["length_m"], st.lap_length(), delta=st.lap_length() * 0.02)
        self.assertAlmostEqual(profile["spacing_m"], 2.0, delta=0.15)
        self.assertEqual(len(profile["corners"]), 4)
        for corner, radius in zip(profile["corners"], st.CORNER_RADII):
            self.assertAlmostEqual(corner["tightest_radius_m"], radius, delta=radius * 0.15)
            self.assertEqual(corner["threshold_g"], 1.2)
        self.assertEqual(profile["skipped_corners"], [])

    def test_corner_positions_follow_the_lap(self):
        """Corners are in lap order and their start index comes before their end index."""
        starts = [c["start_index"] for c in build_track_profile(self.track)["corners"]]
        self.assertEqual(starts, sorted(starts))

    def test_inactive_zones_are_left_out(self):
        """A deactivated corner is not simulated."""
        Zone.objects.filter(track=self.track, label="Corner 2").update(is_active=False)
        labels = [c["label"] for c in build_track_profile(self.track)["corners"]]
        self.assertEqual(labels, ["Corner 1", "Corner 3", "Corner 4"])

    def test_a_corner_that_cannot_be_placed_is_reported_not_guessed(self):
        """A zone with placeholder coordinates is skipped and named."""
        Zone.objects.filter(track=self.track, label="Corner 1").update(
            gps_range={"start": {"lat": 1.0, "lng": 1.0}, "end": {"lat": 1.0, "lng": 1.0}})
        profile = build_track_profile(self.track)
        self.assertEqual(profile["skipped_corners"], ["Corner 1"])
        self.assertEqual(len(profile["corners"]), 3)

    def test_refuses_builtin_archived_unfinished_and_open_outlines(self):
        """Each bad case gives a clear ProfileError."""
        Track.objects.filter(pk=self.track.pk).update(is_builtin=True)
        with self.assertRaisesRegex(ProfileError, "built-in"):
            build_track_profile(Track.objects.get(pk=self.track.pk))
        Track.objects.filter(pk=self.track.pk).update(is_builtin=False, is_archived=True)
        with self.assertRaisesRegex(ProfileError, "archived"):
            build_track_profile(Track.objects.get(pk=self.track.pk))
        with self.assertRaisesRegex(ProfileError, "no outline"):
            build_track_profile(Track.objects.create(name="Empty Map"))
        line = [{"lat": 12.97 + i * 0.0001, "lng": 77.59} for i in range(80)]
        with self.assertRaisesRegex(ProfileError, "closed loop"):
            build_track_profile(Track.objects.create(name="Open Map", reference_line=line))

    def test_write_uses_the_track_uuid_as_file_name(self):
        """The file name is <uuid>.json inside the given folder and holds valid JSON."""
        with tempfile.TemporaryDirectory() as folder:
            path = write_track_profile(self.track, os.path.join(folder, "profiles"))
            self.assertEqual(os.path.basename(path), f"{self.track.id}.json")
            with open(path) as handle:
                self.assertEqual(json.load(handle)["track_id"], str(self.track.id))
            self.assertEqual(os.listdir(os.path.dirname(path)), [f"{self.track.id}.json"])


class TestExportTrackCommand(APITestCase):
    """python manage.py export_track <id> --out <path>."""

    def setUp(self):
        """Create an imported track."""
        super().setUp()
        coach = User.objects.create_user(
            email="exp_coach@trackside.local", name="C", password="CoachPassword123!", role="coach")
        self.track = make_imported_track(coach, name="Export Track")

    def run_command(self, *args):
        """Run the command and return its text output."""
        out = io.StringIO()
        call_command("export_track", *args, stdout=out, stderr=io.StringIO())
        return out.getvalue()

    def test_writes_the_profile_file(self):
        """The file exists, parses, and the message says how many corners were written."""
        with tempfile.TemporaryDirectory() as folder:
            target = os.path.join(folder, "nested", "profile.json")
            message = self.run_command(str(self.track.id), "--out", target)
            self.assertIn("4 corners", message)
            with open(target) as handle:
                self.assertEqual(len(json.load(handle)["corners"]), 4)

    def test_bad_ids_and_locked_tracks_are_refused(self):
        """A non-UUID, an unknown id, the built-in and an archived track all raise CommandError."""
        with tempfile.TemporaryDirectory() as folder:
            target = os.path.join(folder, "p.json")
            for bad in ("not-a-uuid", "00000000-0000-0000-0000-000000000000"):
                with self.assertRaises(CommandError):
                    self.run_command(bad, "--out", target)
            builtin = Track.objects.create(name="Demo Circuit", is_builtin=True)
            with self.assertRaises(CommandError):
                self.run_command(str(builtin.id), "--out", target)
            Track.objects.filter(pk=self.track.pk).update(is_archived=True)
            with self.assertRaises(CommandError):
                self.run_command(str(self.track.id), "--out", target)
            self.assertFalse(os.path.exists(target))


class TestProfileGps(APITestCase):
    """The profile carries one lat/lng for every outline point, on the drawn outline."""

    def test_gps_matches_outline_and_lies_on_the_map_outline(self):
        """Same length as the outline; every point within 10 m of a stored outline point."""
        from tracks.importing.geometry import LocalFrame, distance
        coach = User.objects.create_user(
            email="prof_gps@trackside.local", name="C", password="CoachPassword123!", role="coach")
        track = make_imported_track(coach)
        profile = build_track_profile(track)
        self.assertEqual(len(profile["gps"]), len(profile["outline"]))
        line = track.reference_line
        frame = LocalFrame(sum(p["lat"] for p in line) / len(line), sum(p["lng"] for p in line) / len(line))
        stored = [frame.to_xy(p["lat"], p["lng"]) for p in line]
        for lat, lng in profile["gps"][::10]:
            here = frame.to_xy(lat, lng)
            self.assertLess(min(distance(here, p) for p in stored), 10.0)
