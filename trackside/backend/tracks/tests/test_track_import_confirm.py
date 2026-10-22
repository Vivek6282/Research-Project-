"""
Trackside — Tests for saving an imported map (C5).

Covers permissions, name/label/limit checks, atomic saving, and that the saved
shape comes from the uploaded file, not from numbers sent by the browser.
"""

import json
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from tracks.importing.safe_speed import safe_speed_kmh
from tracks.models import Track, Zone
from tracks.tests import synthetic_track as st

User = get_user_model()
CONFIRM = "/api/tracks/import/confirm/"
PREVIEW = "/api/tracks/import/preview/"


def good_corners(limit=1.2):
    """The user's choices for the four synthetic corners."""
    return [{"number": n, "label": f"Corner {n}", "threshold_g": limit} for n in range(1, 5)]


class TestTrackImportConfirm(APITestCase):
    """Tests for POST /api/tracks/import/confirm/."""

    def setUp(self):
        """Create the users and data this test class needs."""
        super().setUp()
        cache.clear()
        self.coach = User.objects.create_user(
            email="conf_coach@trackside.local", name="Conf Coach", password="CoachPassword123!", role="coach")
        self.driver = User.objects.create_user(
            email="conf_driver@trackside.local", name="Conf Driver", password="DriverPassword123!", role="driver")
        self.text = st.racechrono_csv_text(st.make_samples(laps=3))
        self.client.force_authenticate(self.coach)

    def confirm(self, corners=None, name="Test Circuit", extra=None, user=None):
        """POST a confirm request with sensible defaults."""
        self.client.force_authenticate(user or self.coach)
        data = {
            "file": SimpleUploadedFile("s.csv", self.text.encode(), content_type="text/csv"),
            "name": name,
            "corners": json.dumps(good_corners() if corners is None else corners),
            **(extra or {}),
        }
        return self.client.post(CONFIRM, data, format="multipart")

    def test_saves_track_and_zones_from_the_file(self):
        """201 with a sprint-class track, the file's source, an outline and four named zones."""
        response = self.confirm()
        self.assertEqual(response.status_code, 201, response.data)
        track = Track.objects.get(name="Test Circuit")
        self.assertEqual(track.source, "racechrono_csv")
        self.assertEqual(track.kart_class, Track.KartClass.SPRINT)
        self.assertFalse(track.is_builtin)
        self.assertFalse(track.is_archived)
        self.assertEqual(track.created_by, self.coach)
        self.assertGreater(len(track.reference_line), 250)
        self.assertLessEqual(len(track.reference_line), 2000)
        zones = list(track.zones.order_by("label"))
        self.assertEqual([z.label for z in zones], ["Corner 1", "Corner 2", "Corner 3", "Corner 4"])
        self.assertEqual({z.threshold_g for z in zones}, {1.2})
        self.assertEqual(set(zones[0].gps_range), {"start", "end"})
        self.assertEqual(zones[0].min_threshold_g, 1.0)

    def test_browser_supplied_geometry_is_ignored(self):
        """Extra fields such as reference_line or is_builtin do not reach the saved track."""
        fake = json.dumps([{"lat": 1, "lng": 1}])
        self.confirm(extra={"reference_line": fake, "is_builtin": "true", "source": "vbo"})
        track = Track.objects.get(name="Test Circuit")
        self.assertNotEqual(track.reference_line[0], {"lat": 1, "lng": 1})
        self.assertFalse(track.is_builtin)
        self.assertEqual(track.source, "racechrono_csv")

    def test_driver_is_refused_and_nothing_saved(self):
        """Drivers get 403 and no track appears."""
        self.assertEqual(self.confirm(user=self.driver).status_code, 403)
        self.assertFalse(Track.objects.filter(name="Test Circuit").exists())

    def test_corner_names_must_be_present_short_and_different(self):
        """Blank, 41-character, control-character and duplicate names are all 400."""
        for bad in ("", "   ", "x" * 41, "Bad\x00Name", "Bad\nName"):
            corners = good_corners()
            corners[0]["label"] = bad
            self.assertEqual(self.confirm(corners).status_code, 400, repr(bad))
        corners = good_corners()
        corners[1]["label"] = "corner 1"
        self.assertEqual(self.confirm(corners).status_code, 400)
        corners = good_corners()
        corners[0]["label"] = "x" * 40
        self.assertEqual(self.confirm(corners).status_code, 201)

    def test_limits_must_be_inside_the_sprint_range(self):
        """0.99 and 1.51 g are refused; 1.0 and 1.5 are accepted."""
        for bad in (0.99, 1.51, "abc", None, "nan", 99):
            corners = good_corners()
            corners[2]["threshold_g"] = bad
            self.assertEqual(self.confirm(corners, name=f"T {bad}").status_code, 400, repr(bad))
        corners = good_corners()
        corners[0]["threshold_g"], corners[1]["threshold_g"] = 1.0, 1.5
        self.assertEqual(self.confirm(corners).status_code, 201)

    def test_corner_list_must_match_the_file(self):
        """Too few, too many or wrongly numbered corners are refused; so are broken JSON shapes."""
        self.assertEqual(self.confirm(good_corners()[:3]).status_code, 400)
        self.assertEqual(self.confirm(good_corners() + [{"number": 5, "label": "X", "threshold_g": 1.2}]).status_code, 400)
        wrong = good_corners()
        wrong[3]["number"] = 7
        self.assertEqual(self.confirm(wrong).status_code, 400)
        for raw in ("not json", "{}", "[1, 2]", "[]"):
            self.assertEqual(self.confirm(extra={"corners": raw}).status_code, 400, raw)

    def test_map_name_rules(self):
        """Blank, over-long and duplicate (any case, archived too) names are refused."""
        self.assertEqual(self.confirm(name="").status_code, 400)
        self.assertEqual(self.confirm(name="n" * 151).status_code, 400)
        Track.objects.create(name="Taken Name", is_archived=True)
        response = self.confirm(name="taken name")
        self.assertEqual(response.status_code, 409)
        self.assertIn("already exists", response.data["detail"])

    def test_nothing_is_saved_when_a_zone_fails(self):
        """If saving a zone fails midway the new track is rolled back."""
        with mock.patch.object(Zone.objects, "create", side_effect=RuntimeError("disk full")):
            with self.assertRaises(RuntimeError):
                self.confirm()
        self.assertFalse(Track.objects.filter(name="Test Circuit").exists())

    def test_confirm_is_throttled_to_10_per_hour(self):
        """The 11th confirm request from one user in an hour gets 429."""
        codes = [self.confirm(name="").status_code for _ in range(11)]
        self.assertEqual(codes[:10], [400] * 10)
        self.assertEqual(codes[10], 429)

    def test_radius_option_must_match_between_preview_and_confirm(self):
        """With radius 16 only one corner exists, so four choices no longer fit."""
        self.assertEqual(self.confirm(extra={"corner_radius_m": "16"}).status_code, 400)
        one = self.confirm(corners=good_corners()[:1], extra={"corner_radius_m": "16"})
        self.assertEqual(one.status_code, 201)
        self.assertEqual(Zone.objects.filter(track__name="Test Circuit").count(), 1)


class TestSafeSpeedHint(APITestCase):
    """The safe corner speed = sqrt(limit x 9.81 x radius)."""

    def test_formula(self):
        """1.25 g on a 20 m corner is about 56.4 km/h."""
        self.assertAlmostEqual(safe_speed_kmh(1.25, 20.0), 56.38, places=1)

    def test_preview_reports_range_default_and_hint(self):
        """The preview gives the 1.0-1.5 g range and a hint for each corner at the default limit."""
        cache.clear()
        coach = User.objects.create_user(
            email="hint_coach@trackside.local", name="Hint Coach", password="CoachPassword123!", role="coach")
        self.client.force_authenticate(coach)
        upload = SimpleUploadedFile("s.csv", st.racechrono_csv_text(st.make_samples()).encode(), content_type="text/csv")
        data = self.client.post(PREVIEW, {"file": upload}, format="multipart").data
        self.assertEqual(data["limit_range_g"], {"min": 1.0, "max": 1.5, "default": 1.25})
        first = data["corners"][0]
        self.assertAlmostEqual(
            first["safe_speed_kmh_at_default"], safe_speed_kmh(1.25, first["tightest_radius_m"]), delta=0.2)
