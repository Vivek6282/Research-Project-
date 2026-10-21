"""
Trackside — Tests for the automatic corner finder (C4).

Uses the synthetic rounded-rectangle track whose four corner radii are known
(20, 12, 30 and 25 m in driving order), plus small hand-made loops.
"""

import math
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from tracks.importing import corners as corners_module
from tracks.importing.corners import find_corners, find_runs, merge_close_runs
from tracks.importing.geometry import LocalFrame, resample_closed, smooth_closed
from tracks.importing.outline import Outline, build_outline
from tracks.importing.samples import GpsSample
from tracks.tests import synthetic_track as st

User = get_user_model()
TRUE_RADII = st.CORNER_RADII
ARC_LENGTHS = [r * math.pi / 2 for r in TRUE_RADII]


def synthetic_outline():
    """Outline built from three noisy synthetic laps."""
    return build_outline([GpsSample(a, b, c) for a, b, c in st.make_samples(laps=3)])


def outline_from_points(points, spacing=2.0):
    """Wrap hand-made local points as an Outline (even spacing, lightly smoothed)."""
    return Outline(frame=LocalFrame(12.97, 77.59), points=smooth_closed(points), spacing_m=spacing)


def stadium(straight_m, radius=15.0):
    """Two 180-degree turns joined by two straights, as evenly spaced points."""
    dense = []
    for i in range(int(straight_m * 10) + 1):
        dense.append((i / 10.0, 0.0))
    for i in range(1, 181):
        a = -math.pi / 2 + math.pi * i / 180
        dense.append((straight_m + radius * math.cos(a), radius + radius * math.sin(a)))
    for i in range(1, int(straight_m * 10) + 1):
        dense.append((straight_m - i / 10.0, 2 * radius))
    for i in range(1, 180):
        a = math.pi / 2 + math.pi * i / 180
        dense.append((radius * math.cos(a), radius + radius * math.sin(a)))
    return resample_closed(dense, int(round(sum(math.dist(dense[i], dense[i - 1]) for i in range(1, len(dense))) / 2.0)))


class TestCornerFinder(APITestCase):
    """Tests for find_corners."""

    def test_finds_the_four_corners_in_driving_order(self):
        """Four corners, tightest radii within 15% of 20, 12, 30 and 25 m."""
        found = find_corners(synthetic_outline())
        self.assertEqual(len(found), 4)
        for corner, true_radius in zip(found, TRUE_RADII):
            self.assertAlmostEqual(corner.tightest_radius_m, true_radius, delta=true_radius * 0.15)

    def test_corner_length_is_close_to_the_arc_length(self):
        """Each corner is about as long as its arc (a few metres of run-in either side)."""
        for corner, arc in zip(find_corners(synthetic_outline()), ARC_LENGTHS):
            self.assertGreater(corner.length_m, arc - 4)
            self.assertLess(corner.length_m, arc + 14)

    def test_radius_threshold_changes_which_corners_count(self):
        """A 16 m threshold keeps only the 12 m hairpin; 100 m keeps all four."""
        outline = synthetic_outline()
        self.assertEqual(len(find_corners(outline, 16.0)), 1)
        self.assertEqual(len(find_corners(outline, 100.0)), 4)

    def test_corner_on_the_start_line_is_found_once(self):
        """Starting the loop in the middle of a corner does not split or lose it."""
        outline = synthetic_outline()
        middle = len(outline.points) // 2
        shifted = Outline(frame=outline.frame, points=outline.points[middle:] + outline.points[:middle],
                          spacing_m=outline.spacing_m)
        found = find_corners(shifted)
        self.assertEqual(len(found), 4)
        self.assertEqual(sorted(round(c.tightest_radius_m / 5) for c in found),
                         sorted(round(c.tightest_radius_m / 5) for c in find_corners(outline)))

    def test_corners_closer_than_10_m_are_merged(self):
        """Hairpins joined by a 6 m straight become one corner; a 40 m straight keeps two."""
        self.assertEqual(len(find_corners(outline_from_points(stadium(6.0)))), 1)
        self.assertEqual(len(find_corners(outline_from_points(stadium(40.0)))), 2)

    def test_stretches_shorter_than_8_m_are_dropped(self):
        """Raising the minimum length above every arc removes all corners."""
        with mock.patch.object(corners_module, "MIN_CORNER_LENGTH_M", 200.0):
            self.assertEqual(find_corners(synthetic_outline()), [])

    def test_wide_circle_has_no_corners_and_tight_circle_is_one(self):
        """A 100 m radius circle is not a corner; a 40 m circle is one corner all the way round."""
        def circle(radius):
            """A closed circle outline of the given radius, 2 m between points."""
            return outline_from_points(
                resample_closed([(radius * math.cos(a / 100), radius * math.sin(a / 100)) for a in range(629)],
                                int(2 * math.pi * radius / 2.0)))
        self.assertEqual(find_corners(circle(100.0)), [])
        self.assertEqual(len(find_corners(circle(40.0))), 1)

    def test_run_helpers_handle_edges(self):
        """find_runs and merge_close_runs behave at list ends and across the loop seam."""
        self.assertEqual(find_runs([True, True, False, True]), [(0, 1), (3, 3)])
        self.assertEqual(find_runs([False, False]), [])
        self.assertEqual(merge_close_runs([(2, 5), (7, 9)], 100, 2.0), [(2, 9)])
        self.assertEqual(merge_close_runs([(2, 5), (30, 33)], 100, 2.0), [(2, 5), (30, 33)])
        self.assertEqual(merge_close_runs([(1, 5), (96, 98)], 100, 2.0), [(96, 105)])


class TestCornersInPreview(APITestCase):
    """The preview response carries the corners and accepts the radius option."""

    def setUp(self):
        """Create the users and data this test class needs."""
        super().setUp()
        cache.clear()
        self.coach = User.objects.create_user(
            email="corner_coach@trackside.local", name="Corner Coach", password="CoachPassword123!", role="coach")
        self.client.force_authenticate(self.coach)
        self.text = st.racechrono_csv_text(st.make_samples(laps=3))

    def post(self, extra=None):
        """Upload the synthetic CSV with optional extra form fields."""
        upload = SimpleUploadedFile("s.csv", self.text.encode(), content_type="text/csv")
        return self.client.post("/api/tracks/import/preview/", {"file": upload, **(extra or {})}, format="multipart")

    def test_preview_lists_corners_with_names_and_positions(self):
        """Each corner has Turn n, start/end/apex lat-lng and its tightest radius."""
        response = self.post()
        self.assertEqual(response.status_code, 200, response.data)
        corners = response.data["corners"]
        self.assertEqual([c["suggested_name"] for c in corners], ["Turn 1", "Turn 2", "Turn 3", "Turn 4"])
        self.assertEqual(set(corners[0]["start"]), {"lat", "lng"})
        self.assertAlmostEqual(corners[1]["tightest_radius_m"], 12.0, delta=2.0)
        self.assertEqual(response.data["corner_radius_m"], 60.0)

    def test_radius_option_is_used_and_checked(self):
        """corner_radius_m=16 gives one corner; junk or out-of-range values are 400."""
        self.assertEqual(len(self.post({"corner_radius_m": "16"}).data["corners"]), 1)
        for bad in ("abc", "5", "500", "nan"):
            self.assertEqual(self.post({"corner_radius_m": bad}).status_code, 400, bad)
