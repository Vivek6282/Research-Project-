"""
Trackside — Drawing a track on the map: the clicked points become a saved map with corners and limits.
"""

import math

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APITestCase

from tracks.importing.drawn import build_drawn_outline, parse_drawn_points
from tracks.importing.errors import TrackImportError
from tracks.models import Track, Zone

User = get_user_model()
PREVIEW = "/api/tracks/draw/preview/"
CONFIRM = "/api/tracks/draw/confirm/"
CENTRE_LAT, CENTRE_LNG = 10.0, 76.0
M_PER_DEG = 111_194.9


def stadium(straight_m=220.0, radius_m=28.0, clicks_per_turn=7, clicks_per_straight=4):
    """Clicks around a kart-like track: two straights joined by two tight hairpins, as {lat, lng} points."""
    metres = []
    for k in range(clicks_per_straight):                       # bottom straight, left to right
        metres.append((-straight_m / 2 + straight_m * k / clicks_per_straight, -radius_m))
    for k in range(clicks_per_turn):                           # right hairpin
        a = -math.pi / 2 + math.pi * k / clicks_per_turn
        metres.append((straight_m / 2 + radius_m * math.cos(a), radius_m * math.sin(a)))
    for k in range(clicks_per_straight):                       # top straight, right to left
        metres.append((straight_m / 2 - straight_m * k / clicks_per_straight, radius_m))
    for k in range(clicks_per_turn):                           # left hairpin
        a = math.pi / 2 + math.pi * k / clicks_per_turn
        metres.append((-straight_m / 2 + radius_m * math.cos(a), radius_m * math.sin(a)))
    cos_lat = math.cos(math.radians(CENTRE_LAT))
    return [{"lat": CENTRE_LAT + y / M_PER_DEG, "lng": CENTRE_LNG + x / (M_PER_DEG * cos_lat)} for x, y in metres]


class DrawBase(APITestCase):

    def setUp(self):
        cache.clear()
        self.coach = User.objects.create_user(email="draw_coach@t.test", name="Coach", role="coach", password="CoachPass123!")
        self.driver = User.objects.create_user(email=None, name="Driver", role="driver", password="DriverPass123!")
        self.client.force_authenticate(self.coach)

    def preview(self, points, **extra):
        return self.client.post(PREVIEW, {"points": points, **extra}, format="json")


class TestOutlineFromClicks(DrawBase):

    def test_the_outline_follows_the_clicked_shape(self):
        """About 1,000 m of loop for this stadium, evenly spaced about 2 m apart, with no overshoot beyond the clicks."""
        parsed = parse_drawn_points(stadium())
        outline = build_drawn_outline(parsed.samples)
        expected = 2 * 220 + 2 * math.pi * 28          # two straights and two half circles
        self.assertAlmostEqual(outline.length_m, expected, delta=expected * 0.06)
        self.assertAlmostEqual(outline.spacing_m, 2.0, delta=0.3)
        xs = [x for x, _ in outline.points]
        self.assertLess(max(xs) - min(xs), 220 + 2 * 28 + 6)       # no overshoot past the clicked extent (+ 3 m each side)

    def test_the_curve_is_smooth_not_a_polygon(self):
        """The turn between two clicks is round: the tightest bend measured on the outline is close to the drawn radius."""
        from tracks.importing.corners import radius_profile
        outline = build_drawn_outline(parse_drawn_points(stadium(radius_m=28.0)).samples)
        radii = radius_profile(outline.points, outline.spacing_m)
        self.assertGreater(min(radii), 15.0)         # a jagged polygon would show radii of a few metres
        self.assertLess(min(radii), 40.0)


class TestPreviewEndpoint(DrawBase):

    def test_preview_has_the_same_shape_as_an_import_preview_and_finds_the_two_hairpins(self):
        """The wizard's review step can show it: outline, length, corners with suggested names, limit range."""
        data = self.preview(stadium()).json()
        self.assertEqual(data["source"], "drawn")
        self.assertGreater(len(data["outline"]), 300)
        self.assertEqual(len(data["corners"]), 2)
        self.assertEqual(data["limit_range_g"]["min"], 0.3)
        self.assertTrue(all("suggested_name" in c for c in data["corners"]))
        self.assertEqual(Track.objects.count(), 0)               # a preview saves nothing

    def test_a_looser_radius_finds_the_corners_it_is_told_to(self):
        """The radius option works as it does for imports."""
        self.assertEqual(len(self.preview(stadium(), corner_radius_m=10).json()["corners"]), 0)

    def test_bad_points_are_refused_with_a_clear_message(self):
        """Too few, wrong types, no position, (0,0), too small and too large are all 400 with a detail."""
        good = stadium()
        cases = {
            "too few": good[:5],
            "not a list": "hello",
            "none": None,
            "number as text": [{"lat": "10.0", "lng": "76.0"}] * 10,
            "boolean": [{"lat": True, "lng": False}] * 10,
            "missing lng": [{"lat": 10.0}] * 10,
            "not an object": [[10.0, 76.0]] * 10,
            "zero zero": [{"lat": 0, "lng": 0}] * 10,
            "out of range": [{"lat": 95.0, "lng": 76.0}] * 10,
            "all one place": [{"lat": 10.0, "lng": 76.0}] * 12,
            "tiny": [{"lat": 10.0 + (i % 3) * 1e-6, "lng": 76.0 + (i // 3) * 1e-6} for i in range(12)],
        }
        for label, points in cases.items():
            response = self.client.post(PREVIEW, {"points": points}, format="json")
            self.assertEqual(response.status_code, 400, label)
            self.assertIn("detail", response.json(), label)

    def test_too_many_points_and_too_wide_an_area_are_refused(self):
        """More than 1,000 clicks, or points spread over hundreds of kilometres, are refused."""
        self.assertEqual(self.preview(stadium() * 40).status_code, 400)
        wide = [{"lat": 10.0 + i * 0.5, "lng": 76.0 + (i % 2)} for i in range(12)]
        self.assertEqual(self.preview(wide).status_code, 400)

    def test_double_clicks_do_not_break_it(self):
        """The same point clicked twice in a row, and the first point clicked again to close the loop, are fine."""
        points = stadium()
        doubled = [p for point in points for p in (point, dict(point))] + [dict(points[0])]
        self.assertEqual(self.preview(doubled).status_code, 200)

    def test_a_body_that_is_not_an_object_is_a_400_not_a_crash(self):
        """A bare list or text body is answered 400."""
        for body in ([1, 2, 3], "text"):
            self.assertEqual(self.client.post(PREVIEW, body, format="json").status_code, 400)


class TestConfirmEndpoint(DrawBase):

    def confirm(self, **overrides):
        data = self.preview(stadium()).json()
        corners = [{"number": c["number"], "label": c["suggested_name"], "threshold_g": 0.9} for c in data["corners"]]
        body = {"points": stadium(), "name": "Drawn Test Track", "corners": corners, **overrides}
        return self.client.post(CONFIRM, body, format="json")

    def test_saving_creates_the_track_and_one_zone_per_corner_with_the_chosen_limits(self):
        """A drawn map is saved like an imported one: outline, source 'drawn', corners with limits, who made it."""
        response = self.confirm()
        self.assertEqual(response.status_code, 201, response.content)
        track = Track.objects.get(name="Drawn Test Track")
        self.assertEqual((track.source, track.is_builtin, track.created_by), ("drawn", False, self.coach))
        self.assertGreater(len(track.reference_line), 300)
        zones = list(Zone.objects.filter(track=track))
        self.assertEqual(len(zones), 2)
        self.assertEqual({z.threshold_g for z in zones}, {0.9})

    def test_a_low_limit_below_one_g_is_accepted(self):
        """The coach can set 0.4 g on a slow drawn corner (the floor is 0.3 g)."""
        data = self.preview(stadium()).json()
        corners = [{"number": c["number"], "label": c["suggested_name"], "threshold_g": 0.4} for c in data["corners"]]
        self.assertEqual(self.confirm(corners=corners).status_code, 201)

    def test_an_outline_sent_by_the_browser_is_ignored(self):
        """Only the clicked points matter: a fake outline in the body changes nothing about the saved shape."""
        fake = [{"lat": 1.0, "lng": 1.0}] * 500
        self.assertEqual(self.confirm(outline=fake, reference_line=fake).status_code, 201)
        track = Track.objects.get(name="Drawn Test Track")
        self.assertNotIn({"lat": 1.0, "lng": 1.0}, track.reference_line)

    def test_name_rules_and_corner_rules_are_the_same_as_for_imports(self):
        """A used name is 409, a blank name is 400, a bad limit is 400, the wrong corner list is 400 (nothing saved)."""
        self.assertEqual(self.confirm().status_code, 201)
        self.assertEqual(self.confirm().status_code, 409)                           # same name again
        self.assertEqual(self.confirm(name="  ").status_code, 400)
        bad_limit = [{"number": 1, "label": "A", "threshold_g": 5.0}, {"number": 2, "label": "B", "threshold_g": 0.9}]
        self.assertEqual(self.confirm(name="Other", corners=bad_limit).status_code, 400)
        self.assertEqual(self.confirm(name="Other 2", corners=[]).status_code, 400)
        self.assertEqual(Track.objects.count(), 1)

    def test_the_corner_editor_and_play_demo_see_a_drawn_map_like_any_other(self):
        """The saved map has outline data the corner editor loads and is not locked."""
        self.confirm()
        track = Track.objects.get(name="Drawn Test Track")
        response = self.client.get(f"/api/tracks/{track.id}/corners/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual((len(data["markers"]), data["editable"], data["is_schematic"]), (2, True, False))
        self.assertGreater(len(data["outline"]), 300)


class TestWhoMayDraw(DrawBase):

    def test_only_coach_and_admin(self):
        """A driver and an anonymous visitor are refused on both endpoints; an admin is accepted."""
        admin = User.objects.create_user(email="draw_admin@t.test", name="Admin", role="admin", password="AdminPass123!")
        for who, expected in ((self.driver, 403), (None, 403), (admin, 200)):
            self.client.force_authenticate(who)
            self.assertEqual(self.client.post(PREVIEW, {"points": stadium()}, format="json").status_code, expected)
        self.client.force_authenticate(self.driver)
        self.assertEqual(self.client.post(CONFIRM, {"points": stadium(), "name": "X", "corners": []}, format="json").status_code, 403)
        self.assertEqual(Track.objects.count(), 0)


class TestPlayDemoCanDriveADrawnMap(DrawBase):

    def test_the_simulator_profile_of_a_drawn_map_has_real_coordinates_and_both_corners(self):
        """The Play demo can run the simulated kart round a drawn track: the profile has its outline, corners and lat/lng list."""
        import json
        import tempfile
        from tracks.track_profile import write_track_profile

        data = self.preview(stadium()).json()
        corners = [{"number": c["number"], "label": c["suggested_name"], "threshold_g": 0.9} for c in data["corners"]]
        self.assertEqual(self.client.post(CONFIRM, {"points": stadium(), "name": "Demo Drawn", "corners": corners}, format="json").status_code, 201)
        track = Track.objects.get(name="Demo Drawn")
        with tempfile.TemporaryDirectory() as folder:
            profile = json.load(open(write_track_profile(track, folder, self.driver)))
        self.assertEqual(len(profile["corners"]), 2)
        self.assertGreater(len(profile["outline"]), 300)
        gps = profile["gps"]
        self.assertEqual(len(gps), len(profile["outline"]))
        lats = [p[0] for p in gps]
        lngs = [p[1] for p in gps]
        self.assertAlmostEqual(sum(lats) / len(lats), CENTRE_LAT, delta=0.002)       # the kart's positions are on the drawn spot
        self.assertAlmostEqual(sum(lngs) / len(lngs), CENTRE_LNG, delta=0.002)
