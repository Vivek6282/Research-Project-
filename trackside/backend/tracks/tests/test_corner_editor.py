"""
Trackside — Tests for the corner marker editor, suggestions and duplicate (H3).

Uses the synthetic rounded-rectangle track (corner radii 20, 12, 30 and 25 m)

"""

import math
from unittest import mock

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from driving_sessions.models import Session, Telemetry
from tracks.models import Track, Zone, ZoneThresholdHistory
from tracks.tests.track_factory import make_imported_track

User = get_user_model()


def api_markers(payload):
    """Turn editor markers into the dicts a client would send back."""
    return [{k: m[k] for k in ("id", "label", "threshold_g", "center_index", "length_m")} for m in payload["markers"]]


class EditorBase(APITestCase):
    """Shared users and an imported four-corner track."""

    def setUp(self):
        """Create admin, coach, driver and a custom track."""
        super().setUp()
        make = User.objects.create_user
        self.admin = make(email="ce_admin@trackside.local", name="A", password="AdminPassword123!", role="admin")
        self.coach = make(email="ce_coach@trackside.local", name="C", password="CoachPassword123!", role="coach")
        self.driver = make(email="ce_driver@trackside.local", name="D", password="DriverPassword123!", role="driver")
        self.track = make_imported_track(self.coach, name="Editor Track", limit=1.2)
        self.client.force_authenticate(self.coach)
        self.url = f"/api/tracks/{self.track.id}/corners/"

    def load(self):
        """GET the editor payload."""
        return self.client.get(self.url).data

    def save(self, payload, markers=None, **extra):
        """PUT markers (default: unchanged) against the payload's outline version."""
        body = {"outline_version": payload["outline_version"], "markers": markers if markers is not None else api_markers(payload)}
        body.update(extra)
        return self.client.put(self.url, body, format="json")


class TestEditorRead(EditorBase):
    """What the editor gets when it opens a map."""

    def test_payload_has_outline_markers_suggestions_and_limits(self):
        """Outline, per-point radii, four placed markers, four suggestions and the limit ranges."""
        data = self.load()
        self.assertTrue(data["editable"])
        self.assertLessEqual(len(data["outline"]), 2000)
        self.assertEqual(len(data["radii"]), len(data["outline"]))
        self.assertEqual(len(data["markers"]), 4)
        self.assertTrue(all(m["center_index"] is not None and m["radius_m"] for m in data["markers"]))
        self.assertEqual(data["limit_range_g"], {"min": 0.3, "max": 1.5, "default": 1.25})
        self.assertEqual(data["zone_length_m"], {"min": 10.0, "max": 100.0, "default": 30.0})
        self.assertEqual(len(data["suggestions"]), 4)

    def test_suggestions_are_the_tightest_point_of_each_bend(self):
        """Suggestion radii match the true corner radii and sit inside the existing markers."""
        data = self.load()
        radii = sorted(s["radius_m"] for s in data["suggestions"])
        for got, true in zip(radii, sorted([20.0, 12.0, 30.0, 25.0])):
            self.assertAlmostEqual(got, true, delta=true * 0.2)
        self.assertTrue(all(s["already_marked"] for s in data["suggestions"]))

    def test_a_new_corner_shows_as_not_yet_marked(self):
        """After removing a marker, its bend is suggested again (already_marked False)."""
        data = self.load()
        self.assertEqual(self.save(data, api_markers(data)[1:]).status_code, 200)
        self.assertEqual(sum(1 for s in self.load()["suggestions"] if not s["already_marked"]), 1)

    def test_driver_and_anonymous_are_refused(self):
        """Only Admin and Coach can open the editor."""
        self.client.force_authenticate(self.driver)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.put(self.url, {}, format="json").status_code, 403)
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(self.url).status_code, (401, 403))
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(self.url).status_code, 200)


class TestEditorSave(EditorBase):
    """Saving markers as zones."""

    def test_add_rename_and_change_limit(self):
        """A new marker becomes a zone; a rename and a limit change are saved, the limit with history."""
        data = self.load()
        markers = api_markers(data)
        markers[0]["label"] = "Hairpin Left"
        markers[0]["threshold_g"] = 1.1
        markers.append({"id": None, "label": "Mid Straight", "threshold_g": 1.4, "center_index": 20, "length_m": 40})
        response = self.save(data, markers)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["saved"]["created"], 1)
        zones = {z.label: z for z in self.track.zones.filter(is_active=True)}
        self.assertEqual(len(zones), 5)
        renamed = zones["Hairpin Left"]
        self.assertEqual(renamed.threshold_g, 1.1)
        self.assertEqual(ZoneThresholdHistory.objects.get(zone=renamed, new_g=1.1).old_g, 1.2)
        self.assertEqual(zones["Mid Straight"].threshold_g, 1.4)

    def test_zone_segment_is_centred_with_the_requested_length(self):
        """gps_range holds start, end and centre; the straight line start-to-end is no longer than the zone."""
        data = self.load()
        markers = api_markers(data)[:1] + [{"id": None, "label": "Wide", "threshold_g": 1.3, "center_index": 150, "length_m": 60}]
        self.assertEqual(self.save(data, markers).status_code, 200)
        zone = Zone.objects.get(track=self.track, label="Wide")
        box = zone.gps_range
        self.assertEqual(set(box), {"start", "end", "center", "length_m"})
        self.assertEqual(box["length_m"], 60)
        span = math.hypot((box["end"]["lat"] - box["start"]["lat"]) * 111195,
                          (box["end"]["lng"] - box["start"]["lng"]) * 111195 * math.cos(math.radians(12.97)))
        self.assertLessEqual(span, 61)
        self.assertGreater(span, 40)
        centre = data["outline"][150]
        self.assertAlmostEqual(box["center"]["lat"], centre["lat"], places=6)

    def test_marker_without_history_is_deleted(self):
        """Removing a marker whose zone has no telemetry or alerts deletes the zone."""
        data = self.load()
        response = self.save(data, api_markers(data)[:3])
        self.assertEqual(response.data["saved"]["deleted"], 1)
        self.assertEqual(self.track.zones.count(), 3)

    def test_marker_with_telemetry_is_deactivated_and_hidden(self):
        """The zone stays (with its readings) but disappears from the editor, track and zone list."""
        data = self.load()
        victim = Zone.objects.get(track=self.track, label="Corner 2")
        session = Session.objects.create(driver=self.driver, track=self.track, started_at=timezone.now())
        Telemetry.objects.create(session=session, zone=victim, lateral_g=1.0, speed_kmh=50, gps_lat=0, gps_lng=0, recorded_at=timezone.now())
        markers = [m for m in api_markers(data) if m["id"] != str(victim.id)]
        response = self.save(data, markers)
        self.assertEqual(response.data["saved"]["deactivated"], 1)
        victim.refresh_from_db()
        self.assertFalse(victim.is_active)
        self.assertEqual(victim.telemetry_readings.count(), 1)
        self.assertNotIn("Corner 2", [m["label"] for m in response.data["markers"]])
        self.assertNotIn("Corner 2", [z["label"] for z in self.client.get(f"/api/tracks/{self.track.id}/").data["zones"]])

    def test_validation_errors_give_clear_messages_and_save_nothing(self):
        """Every bad marker is refused with 400 and the zones are unchanged."""
        data = self.load()
        good = api_markers(data)

        def with_change(**change):
            """The good markers with the first one changed."""
            return [dict(good[0], **change)] + good[1:]

        bad_cases = {
            "blank name": with_change(label="  "),
            "41-character name": with_change(label="x" * 41),
            "control character": with_change(label="a\x00b"),
            "Straight": with_change(label="Straight"),
            "Straightaway": with_change(label="straightaway kink"),
            "duplicate name": with_change(label=good[1]["label"].upper()),
            "limit too low": with_change(threshold_g=0.29),
            "limit too high": with_change(threshold_g=1.51),
            "limit text": with_change(threshold_g="1.2"),
            "zone too short": with_change(length_m=9.9),
            "zone too long": with_change(length_m=100.1),
            "off the outline": with_change(center_index=99999),
            "not placed": with_change(center_index=None),
            "overlap": with_change(center_index=good[1]["center_index"]),
        }
        for name, markers in bad_cases.items():
            response = self.save(data, markers)
            self.assertEqual(response.status_code, 400, f"{name}: {response.data}")
            self.assertIn("detail", response.data)
        self.assertEqual(self.track.zones.filter(is_active=True).count(), 4)
        self.assertEqual(self.save(data, "nope").status_code, 400)
        self.assertEqual(self.save(data, [dict(good[0], label=f"c{i}", center_index=i * 4) for i in range(61)]).status_code, 400)

    def test_boundary_values_are_accepted(self):
        """0.3 g, 1.5 g, 10 m and 100 m are allowed; 40-character names are allowed."""
        data = self.load()
        markers = api_markers(data)
        markers[0].update(threshold_g=0.3, length_m=10, label="n" * 40)
        markers[1].update(threshold_g=1.5, length_m=100)
        self.assertEqual(self.save(data, markers[:2]).status_code, 200)

    def test_stale_outline_and_unknown_ids_are_refused(self):
        """A save against an old outline version, or with an unknown corner id, is a 409."""
        data = self.load()
        self.assertEqual(self.save(data, outline_version="old").status_code, 409)
        markers = api_markers(data)
        markers[0]["id"] = "00000000-0000-0000-0000-000000000000"
        self.assertEqual(self.save(data, markers).status_code, 409)

    def test_save_is_all_or_nothing(self):
        """If creating a zone fails halfway nothing is changed."""
        data = self.load()
        markers = api_markers(data)
        markers[0]["label"] = "Renamed"
        markers.append({"id": None, "label": "New A", "threshold_g": 1.2, "center_index": 20, "length_m": 20})
        with mock.patch.object(Zone.objects, "create", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                self.save(data, markers)
        self.assertFalse(Zone.objects.filter(label="Renamed").exists())

    def test_archived_track_cannot_be_edited(self):
        """An archived map answers 409 to PUT but can still be read."""
        data = self.load()
        Track.objects.filter(pk=self.track.pk).update(is_archived=True)
        self.assertEqual(self.save(data).status_code, 409)
        self.assertFalse(self.client.get(self.url).data["editable"])


class TestDuplicate(EditorBase):
    """Duplicating a map makes an editable copy of its outline and corners."""

    def test_duplicate_makes_an_editable_copy_and_leaves_the_original_alone(self):
        """The copy has the outline and all four corners with the same limits; the original is unchanged."""
        response = self.client.post(f"/api/tracks/{self.track.id}/duplicate/", {"name": "My Copy"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        copy = Track.objects.get(name="My Copy")
        self.assertEqual(copy.source, "manual")
        self.assertAlmostEqual(len(copy.reference_line), len(self.track.reference_line), delta=10)
        self.assertEqual({z.threshold_g for z in copy.zones.all()}, {1.2})
        self.assertEqual(response.data["clamped"], [])
        self.assertEqual(self.track.zones.count(), 4)
        editable = self.client.get(f"/api/tracks/{copy.id}/corners/").data
        self.assertTrue(editable["editable"])
        self.assertEqual(len(editable["markers"]), 4)
        self.assertTrue(all(m["center_index"] is not None for m in editable["markers"]))

    def test_duplicate_keeps_corner_types(self):
        """A corner's type is copied along with its name and limit."""
        Zone.objects.filter(track=self.track, label="Corner 1").update(corner_type="hairpin")
        self.client.post(f"/api/tracks/{self.track.id}/duplicate/", {"name": "Typed Copy"}, format="json")
        self.assertEqual(Zone.objects.get(track__name="Typed Copy", label="Corner 1").corner_type, "hairpin")

    def test_duplicate_rules(self):
        """Name is required and unique (any case); drivers cannot duplicate; an archived map can be copied."""
        url = f"/api/tracks/{self.track.id}/duplicate/"
        self.assertEqual(self.client.post(url, {}, format="json").status_code, 400)
        self.assertEqual(self.client.post(url, {"name": "editor track"}, format="json").status_code, 409)
        self.client.force_authenticate(self.driver)
        self.assertEqual(self.client.post(url, {"name": "X"}, format="json").status_code, 403)
        self.client.force_authenticate(self.coach)
        Track.objects.filter(pk=self.track.pk).update(is_archived=True)
        copy = self.client.post(url, {"name": "Editor Copy"}, format="json")
        self.assertEqual(copy.status_code, 201, copy.data)
        self.assertEqual(Track.objects.get(name="Editor Copy").zones.count(), 4)
        self.assertFalse(Track.objects.get(name="Editor Copy").is_archived)
