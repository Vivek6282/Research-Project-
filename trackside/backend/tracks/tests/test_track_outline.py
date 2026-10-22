"""
Trackside — Tests for building the track outline (C3).

Uses the synthetic rounded-rectangle track (602.7 m per lap, known shape).
"""

import math
import os

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from tracks.importing.errors import TrackImportError
from tracks.importing.outline import MAX_OUTLINE_POINTS, build_outline
from tracks.importing.racechrono_csv import parse_racechrono_csv
from tracks.importing.samples import GpsSample
from tracks.importing.vbo import parse_vbo
from tracks.tests import synthetic_track as st

User = get_user_model()
FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
TRUE_LENGTH = st.lap_length()


def samples_from(raw):
    """Turn (lat, lng, lap) tuples into GpsSample objects."""
    return [GpsSample(lat=lat, lng=lng, lap=lap) for lat, lng, lap in raw]


def distance_to_true_track(outline_point):
    """Smallest distance (m) from an outline lat/lng point to the true synthetic lap."""
    x = (outline_point["lng"] - st.ORIGIN_LNG) * st.METERS_PER_DEG_LAT * math.cos(math.radians(st.ORIGIN_LAT))
    y = (outline_point["lat"] - st.ORIGIN_LAT) * st.METERS_PER_DEG_LAT
    return min(math.hypot(x - px, y - py)
               for px, py in (st.position_at(d * 0.5) for d in range(int(TRUE_LENGTH * 2) + 1)))


class TestTrackOutline(APITestCase):
    """Tests for lap selection, resampling and smoothing."""

    def test_lap_numbered_file_gives_one_lap(self):
        """Three laps in the file still give an outline about one lap long."""
        outline = build_outline(samples_from(st.make_samples(laps=3)))
        self.assertAlmostEqual(outline.length_m, TRUE_LENGTH, delta=TRUE_LENGTH * 0.01)

    def test_file_without_lap_column_finds_the_loop(self):
        """With no lap numbers the loop is found where the path comes back to the start."""
        text = st.racechrono_csv_text(st.make_samples(laps=3), with_lap=False)
        outline = build_outline(parse_racechrono_csv(text).samples)
        self.assertAlmostEqual(outline.length_m, TRUE_LENGTH, delta=TRUE_LENGTH * 0.02)

    def test_vbo_fixture_gives_one_lap(self):
        """The synthetic VBO (no lap column, two laps) gives one lap."""
        with open(os.path.join(FIXTURES, "synthetic_track.vbo")) as handle:
            outline = build_outline(parse_vbo(handle.read()).samples)
        self.assertAlmostEqual(outline.length_m, TRUE_LENGTH, delta=TRUE_LENGTH * 0.02)

    def test_points_are_evenly_spaced_about_2_metres(self):
        """Neighbouring outline points are about 2 m apart."""
        outline = build_outline(samples_from(st.make_samples(laps=2)))
        gaps = [math.dist(outline.points[i], outline.points[(i + 1) % len(outline.points)])
                for i in range(len(outline.points))]
        self.assertAlmostEqual(outline.spacing_m, 2.0, places=2)
        self.assertLess(max(gaps), 2.2)
        self.assertGreater(min(gaps), 1.7)

    def test_outline_stays_close_to_the_true_track(self):
        """After smoothing, every point is within 1 m of the real shape (GPS noise is 0.25 m)."""
        outline = build_outline(samples_from(st.make_samples(laps=2)))
        worst = max(distance_to_true_track(p) for p in outline.as_lat_lng()[::5])
        self.assertLess(worst, 1.0)

    def test_partial_and_odd_laps_are_not_chosen(self):
        """A half lap and a long wandering lap lose to the typical closed lap."""
        full = st.make_samples(laps=3)
        per_lap = len(full) // 3
        partial = [(a, b, 1) for a, b, _ in full[: per_lap // 2]]
        typical = [(a, b, 2) for a, b, _ in full[per_lap: 2 * per_lap]]
        typical2 = [(a, b, 3) for a, b, _ in full[2 * per_lap:]]
        outline = build_outline(samples_from(partial + typical + typical2))
        self.assertAlmostEqual(outline.length_m, TRUE_LENGTH, delta=TRUE_LENGTH * 0.01)

    def test_no_closed_lap_is_a_clear_error(self):
        """A straight run that never returns to its start is refused."""
        straight = [(st.ORIGIN_LAT + i * 0.00002, st.ORIGIN_LNG, 1) for i in range(120)]
        with self.assertRaises(TrackImportError):
            build_outline(samples_from(straight))

    def test_very_long_track_is_capped_at_2000_points(self):
        """A 5 km loop widens the spacing instead of exceeding 2,000 points."""
        radius = 800.0
        ring = []
        for i in range(1200):
            angle = 2 * math.pi * i / 1200
            lat, lng = st.to_lat_lng(radius * math.cos(angle), radius * math.sin(angle))
            ring.append((lat, lng, 1))
        outline = build_outline(samples_from(ring + ring[:1]))
        self.assertLessEqual(len(outline.points), MAX_OUTLINE_POINTS)
        self.assertGreater(outline.spacing_m, 2.0)


class TestOutlineInPreview(APITestCase):
    """The preview response carries the outline."""

    def test_preview_returns_outline_points(self):
        """POST preview returns at most 2,000 lat/lng points and a length near 603 m."""
        cache.clear()
        coach = User.objects.create_user(
            email="outline_coach@trackside.local", name="Outline Coach", password="CoachPassword123!", role="coach")
        self.client.force_authenticate(coach)
        text = st.racechrono_csv_text(st.make_samples(laps=3))
        upload = SimpleUploadedFile("s.csv", text.encode(), content_type="text/csv")
        response = self.client.post("/api/tracks/import/preview/", {"file": upload}, format="multipart")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertLessEqual(len(response.data["outline"]), 2000)
        self.assertGreater(len(response.data["outline"]), 250)
        self.assertEqual(set(response.data["outline"][0]), {"lat", "lng"})
        self.assertAlmostEqual(response.data["outline_length_m"], TRUE_LENGTH, delta=TRUE_LENGTH * 0.01)
