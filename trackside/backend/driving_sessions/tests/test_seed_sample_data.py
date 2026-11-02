"""
Trackside — Tests for the seed_sample_data management command (a finished sample session on a chosen map).
"""

import io

from django.core.management import CommandError, call_command
from rest_framework.test import APITestCase

from driving_sessions.models import Session, Telemetry
from tracks.models import Track, Zone

SQUARE = [{"lat": 12.97, "lng": 77.59}, {"lat": 12.971, "lng": 77.59}, {"lat": 12.971, "lng": 77.591}, {"lat": 12.97, "lng": 77.591}]


class TestSeedSampleData(APITestCase):
    """The command needs an existing map with an outline and the three simulator corners."""

    def setUp(self):
        """A map with an outline and Hairpin, Sweeper and Chicane."""
        super().setUp()
        self.track = Track.objects.create(name="Sample Map", kart_class=Track.KartClass.SPRINT, reference_line=SQUARE)
        for label, limit in (("Hairpin", 1.15), ("Sweeper", 1.4), ("Chicane", 1.3)):
            Zone.objects.create(track=self.track, label=label, threshold_g=limit)

    def run_seed(self):
        """Run the command on the test map."""
        call_command("seed_sample_data", track_name="Sample Map", stdout=io.StringIO())

    def test_creates_one_finished_sample_session_on_the_chosen_map_and_repeats_do_nothing(self):
        """Readings use the map's own outline; running twice makes no second session; no map is created."""
        self.run_seed()
        session = Session.objects.get()
        self.assertEqual((session.track, session.is_demo, session.kart_number), (self.track, True, "Sample"))
        self.assertIsNotNone(session.ended_at)
        first = Telemetry.objects.filter(session=session).first()
        self.assertIn((first.gps_lat, first.gps_lng), {(p["lat"], p["lng"]) for p in SQUARE})
        self.run_seed()
        self.assertEqual(Session.objects.count(), 1)
        self.assertEqual(Track.objects.count(), 1)

    def test_refuses_an_unknown_map_a_map_without_corners_and_a_map_without_an_outline(self):
        """Clear errors, and nothing is created."""
        with self.assertRaisesRegex(CommandError, "No active map"):
            call_command("seed_sample_data", track_name="Nope", stdout=io.StringIO())
        Track.objects.filter(pk=self.track.pk).update(reference_line=None)
        with self.assertRaisesRegex(CommandError, "no outline"):
            self.run_seed()
        Zone.objects.filter(track=self.track, label="Sweeper").delete()
        with self.assertRaisesRegex(CommandError, "no corner called Sweeper"):
            self.run_seed()
        self.assertEqual(Session.objects.count(), 0)
