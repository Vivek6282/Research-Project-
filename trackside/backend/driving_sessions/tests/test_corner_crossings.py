"""
Trackside — Tests for timing each corner crossing (Phase 2.0, task 1c).

Readings are 0.5 s apart unless a test says otherwise, so the reading interval
is 0.5 s and every number below is hand-worked.
"""

from datetime import timedelta

from django.test import SimpleTestCase

from driving_sessions.corner_deltas import split_into_crossings
from driving_sessions.tests.test_corner_deltas import START, CornerDeltasBase


class TestCrossingsThroughTheEndpoint(CornerDeltasBase):
    """Corner times when a crossing does not line up with lap numbers."""

    def test_corner_across_the_start_finish_line_stays_in_one_piece(self):
        """Z is entered on lap 1 and left on lap 2: one 2.5 s crossing on lap 1, not two broken ones."""
        z = self.zone_z
        self.add([(1, None)] * 4 + [(1, z)] * 3 + [(2, z)] * 2 + [(2, None)] * 4 + [(2, z)] * 2 + [(3, None)] * 4)
        laps = [(l["lap_number"], l["time_s"]) for l in self.corner(self.get(self.coach), "Turn Z")["laps"]]
        self.assertEqual(laps, [(1, 2.5), (2, 1.0)])

    def test_one_reading_outside_the_corner_is_treated_as_gps_flicker(self):
        """Z x3, one reading outside, Z x2 on the same lap = one crossing from first to last: 3.0 s."""
        z = self.zone_z
        self.add([(1, z)] * 3 + [(1, None)] + [(1, z)] * 2 + [(2, None)] * 4)
        self.assertEqual(self.corner(self.get(self.coach), "Turn Z")["laps"][0]["time_s"], 3.0)

    def test_second_separate_crossing_on_the_same_lap_does_not_stretch_the_time(self):
        """Z x2, 2 s away, Z x4 on one lap: the first crossing (1.0 s) counts, not a 4 s span."""
        z = self.zone_z
        self.add([(1, z)] * 2 + [(1, None)] * 4 + [(1, z)] * 4 + [(2, None)] * 4)
        self.assertEqual(self.corner(self.get(self.coach), "Turn Z")["laps"][0]["time_s"], 1.0)

    def test_lap_comes_from_a_later_reading_when_the_entry_has_none(self):
        """The first reading in the corner has no lap number; the crossing still lands on lap 1."""
        z = self.zone_z
        self.add([(None, z)] + [(1, z)] * 2 + [(2, None)] * 4)
        self.assertEqual([l["lap_number"] for l in self.corner(self.get(self.coach), "Turn Z")["laps"]], [1])


class TestSplitIntoCrossings(SimpleTestCase):
    """The grouping rule on its own, without the database."""

    def at(self, seconds):
        """A reading time this many seconds after the start."""
        return START + timedelta(seconds=seconds)

    def test_long_gap_inside_a_corner_ends_the_crossing(self):
        """A 5 s silence (over the 3 s limit) splits one corner into two crossings."""
        crossings = split_into_crossings([(self.at(0), "z", 1), (self.at(0.5), "z", 1), (self.at(5.5), "z", 1)])
        self.assertEqual([(c["first"], c["last"]) for c in crossings],
                         [(self.at(0), self.at(0.5)), (self.at(5.5), self.at(5.5))])

    def test_changing_corner_ends_the_crossing(self):
        """Back-to-back corners give one crossing each."""
        crossings = split_into_crossings([(self.at(0), "z", 1), (self.at(0.5), "a", 1)])
        self.assertEqual([c["zone_id"] for c in crossings], ["z", "a"])

    def test_readings_outside_every_corner_give_no_crossings(self):
        """Straights only: nothing to time."""
        self.assertEqual(split_into_crossings([(self.at(0), None, 1), (self.at(0.5), None, 1)]), [])
