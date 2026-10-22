"""
Trackside — Tests for the track import preview upload (C2).

Covers permissions, file safety limits, row validation, the RaceChrono CSV and
VBO readers, the throttle, and that nothing is saved at preview time.
"""

import os

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from tracks.importing.racechrono_csv import parse_racechrono_csv
from tracks.importing.vbo import minutes_to_position, parse_vbo
from tracks.models import Track
from tracks.tests import synthetic_track as st

User = get_user_model()
URL = "/api/tracks/import/preview/"
FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def upload(name, content):
    """Wrap text or bytes as an uploaded file."""
    data = content.encode() if isinstance(content, str) else content
    return SimpleUploadedFile(name, data, content_type="text/plain")


def tiny_csv(rows):
    """Build a minimal CSV with only latitude and longitude from (lat, lng) text pairs."""
    return "latitude,longitude\n" + "".join(f"{a},{b}\n" for a, b in rows)


class TestTrackImportUpload(APITestCase):
    """Tests for POST /api/tracks/import/preview/."""

    def setUp(self):
        """Create the users and data this test class needs."""
        super().setUp()
        cache.clear()
        self.coach = User.objects.create_user(
            email="imp_coach@trackside.local", name="Imp Coach", password="CoachPassword123!", role="coach")
        self.admin = User.objects.create_user(
            email="imp_admin@trackside.local", name="Imp Admin", password="AdminPassword123!", role="admin")
        self.driver = User.objects.create_user(
            email="imp_driver@trackside.local", name="Imp Driver", password="DriverPassword123!", role="driver")
        self.csv_text = st.racechrono_csv_text(st.make_samples(laps=3))

    def post(self, name, content, user=None):
        """POST one file as the given user (coach by default)."""
        self.client.force_authenticate(user or self.coach)
        return self.client.post(URL, {"file": upload(name, content)}, format="multipart")

    def test_coach_and_admin_can_preview_a_csv(self):
        """Both allowed roles get a 200 with row counts and file metadata."""
        for user in (self.coach, self.admin):
            response = self.post("session.csv", self.csv_text, user)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["source"], "racechrono_csv")
            self.assertEqual(response.data["track_name"], "Synthetic Test Track")
            self.assertEqual(response.data["rows_rejected"], 3)
            self.assertEqual(response.data["rows_used"], response.data["rows_total"] - 3)

    def test_driver_and_anonymous_are_refused(self):
        """Drivers get 403 and logged-out callers cannot upload."""
        self.assertEqual(self.post("a.csv", self.csv_text, self.driver).status_code, 403)
        self.client.force_authenticate(None)
        response = self.client.post(URL, {"file": upload("a.csv", self.csv_text)}, format="multipart")
        self.assertIn(response.status_code, (401, 403))

    def test_preview_saves_nothing(self):
        """No Track or Zone is created by a preview."""
        before = Track.objects.count()
        self.assertEqual(self.post("a.csv", self.csv_text).status_code, 200)
        self.assertEqual(Track.objects.count(), before)

    def test_only_csv_and_vbo_extensions_are_accepted(self):
        """A .txt, .exe or extensionless name is rejected with 400."""
        for name in ("a.txt", "a.exe", "noextension", "a.csv.exe"):
            self.assertEqual(self.post(name, self.csv_text).status_code, 400, name)

    def test_missing_file_is_400(self):
        """A request with no file field gets a clear 400."""
        self.client.force_authenticate(self.coach)
        self.assertEqual(self.client.post(URL, {}, format="multipart").status_code, 400)

    def test_json_body_is_refused(self):
        """Only multipart uploads are accepted."""
        self.client.force_authenticate(self.coach)
        self.assertEqual(self.client.post(URL, {"file": "x"}, format="json").status_code, 415)

    def test_file_over_5_mb_is_413(self):
        """A file one byte over 5 MB is refused."""
        big = "latitude,longitude\n" + "x" * (5 * 1024 * 1024)
        self.assertEqual(self.post("big.csv", big).status_code, 413)

    def test_more_than_200000_rows_is_refused(self):
        """200,001 data rows is over the row limit."""
        text = tiny_csv([("12.97", "77.59")] * 200_001)
        self.assertLess(len(text), 5 * 1024 * 1024)
        response = self.post("rows.csv", text)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Too many data rows", response.data["detail"])

    def test_exactly_200000_rows_is_allowed(self):
        """The row limit itself is allowed."""
        parsed = parse_racechrono_csv(tiny_csv([("12.97", "77.59")] * 200_000))
        self.assertEqual(parsed.rows_total, 200_000)

    def test_binary_and_non_utf8_files_are_refused(self):
        """Null bytes and invalid UTF-8 give a 400, not a crash."""
        self.assertEqual(self.post("a.csv", b"latitude,longitude\n\x00\x01\x02").status_code, 400)
        self.assertEqual(self.post("a.csv", b"latitude,longitude\n\xff\xfe\xfa\n").status_code, 400)

    def test_bad_rows_are_dropped_and_counted(self):
        """NaN, infinite, out-of-range, text and (0,0) rows never reach the samples."""
        good = [(f"12.{970 + i}", f"77.{590 + i}") for i in range(60)]
        bad = [("nan", "77.5"), ("12.9", "inf"), ("91", "77"), ("12", "181"),
               ("0", "0"), ("abc", "def"), ("-91.0", "5")]
        parsed = parse_racechrono_csv(tiny_csv(good + bad))
        self.assertEqual(len(parsed.samples), 60)
        self.assertEqual(parsed.rows_rejected, len(bad))

    def test_too_few_good_rows_is_400(self):
        """Fewer than 50 usable rows cannot make a track."""
        response = self.post("few.csv", tiny_csv([("12.97", "77.59")] * 10))
        self.assertEqual(response.status_code, 400)

    def test_csv_without_gps_columns_is_400(self):
        """A CSV with no latitude/longitude header is not accepted."""
        self.assertEqual(self.post("a.csv", "a,b\n1,2\n").status_code, 400)

    def test_gps_source_columns_are_preferred_over_calculated(self):
        """With two latitude channels the one marked 'gps' is used."""
        parsed = parse_racechrono_csv(self.csv_text)
        self.assertAlmostEqual(parsed.samples[0].lat, st.ORIGIN_LAT, delta=0.0005)
        self.assertEqual({s.lap for s in parsed.samples}, {1, 2, 3})

    def test_csv_formulas_and_html_are_treated_as_plain_text(self):
        """Odd cell text is never evaluated; it is just a bad row."""
        rows = [("=1+1", "<script>"), ("12.97", "77.59")] * 30
        parsed = parse_racechrono_csv(tiny_csv(rows))
        self.assertEqual(len(parsed.samples), 30)

    def test_vbo_minutes_and_west_positive_sign_are_converted(self):
        """VBO minutes become degrees and 'positive = West' becomes negative longitude."""
        lat, lng = minutes_to_position(778.2960, -4655.6898)
        self.assertAlmostEqual(lat, 12.9716, places=4)
        self.assertAlmostEqual(lng, 77.5948, places=4)
        west_lat, west_lng = minutes_to_position(3169.3, 5399.0)
        self.assertLess(west_lng, 0)
        self.assertEqual(minutes_to_position(6000.0, 0.0), (None, None))

    def test_vbo_file_parses_through_the_endpoint(self):
        """The synthetic VBO fixture previews as source 'vbo' near the origin."""
        with open(os.path.join(FIXTURES, "synthetic_track.vbo")) as handle:
            text = handle.read()
        response = self.post("session.vbo", text)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["source"], "vbo")
        parsed = parse_vbo(text)
        self.assertAlmostEqual(parsed.samples[0].lng, st.ORIGIN_LNG, delta=0.0005)

    def test_vbo_missing_sections_is_400(self):
        """A .vbo without [column names]/[data] is refused."""
        self.assertEqual(self.post("a.vbo", "hello\nworld\n").status_code, 400)

    def test_eleventh_import_in_an_hour_is_throttled(self):
        """The 11th request from one user within the hour gets 429."""
        codes = [self.post("a.txt", "x").status_code for _ in range(11)]
        self.assertEqual(codes[:10], [400] * 10)
        self.assertEqual(codes[10], 429)

    def test_real_racechrono_sample_if_present(self):
        """If the real export is in the fixtures folder, it must parse and preview."""
        path = os.path.join(FIXTURES, "racechrono_sample.csv")
        if not os.path.exists(path):
            self.skipTest("racechrono_sample.csv (real export) is not in the repo yet")
        with open(path, encoding="utf-8-sig") as handle:
            response = self.post("racechrono_sample.csv", handle.read())
        self.assertEqual(response.status_code, 200, response.data)
