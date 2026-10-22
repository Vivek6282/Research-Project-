"""
Unit tests for the track-profile physics (SIM-2, SIM-3).

Uses tests/fixtures/synthetic_profile.json: a SYNTHETIC rounded-rectangle track
(four corners, limit 1.2 g) exported by the real export_track code.
"""

import io
import os
import sys
import unittest
from unittest import mock

demo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if demo_dir not in sys.path:
    sys.path.insert(0, demo_dir)

import sim_profile_run
from sim_physics import ProfileSimulator, TIME_STEP_S, speed_profile
from sim_profile import load_profile

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "synthetic_profile.json")
LIMIT = 1.2


def lap_packets(pace, seed, laps=3):
    """All packets of several laps for one pace and seed."""
    simulator = ProfileSimulator(load_profile(FIXTURE), pace, seed=seed)
    return [p for lap in range(1, laps + 1) for p in simulator.lap_packets(lap)]


def corner_peaks(packets):
    """Highest g and stage of each corner in each lap: {(lap, zone): (g, stage)}."""
    peaks = {}
    for p in packets:
        if p["zone"] != "Straight":
            key = (p["lap"], p["zone"])
            if key not in peaks or p["g_force"] > peaks[key][0]:
                peaks[key] = (p["g_force"], p["stage"])
    return peaks


class PaceTests(unittest.TestCase):
    """Each pace shows its colour at every corner on every lap."""

    def test_safe_pace_stays_green(self):
        """Safe: every reading in every corner is NOMINAL and peaks near 0.72 x limit (plus corner jumps)."""
        packets = lap_packets("safe", seed=1, laps=8)
        self.assertEqual({p["stage"] for p in packets}, {"NOMINAL"})
        for g, _ in corner_peaks(packets).values():
            self.assertAlmostEqual(g, 0.7225 * LIMIT, delta=0.09 * LIMIT)

    def test_edge_pace_is_amber_never_red(self):
        """Edge: each corner peaks in MONITORING and never reaches INTERVENE."""
        peaks = corner_peaks(lap_packets("edge", seed=2, laps=15))
        self.assertEqual({stage for _, stage in peaks.values()}, {"MONITORING"})
        self.assertLess(max(g for g, _ in peaks.values()), LIMIT)

    def test_over_pace_is_red_in_every_corner(self):
        """Over: each corner reaches INTERVENE on every lap."""
        peaks = corner_peaks(lap_packets("over", seed=3, laps=8))
        self.assertEqual(len(peaks), 4 * 8)
        self.assertEqual({stage for _, stage in peaks.values()}, {"INTERVENE"})

    def test_corner_readings_jump_more_than_straight_readings(self):
        """Inside a corner the readings swing much more than on a straight."""
        packets = lap_packets("safe", seed=6, laps=3)
        def spread(rows):
            values = [p["g_force"] for p in rows]
            return max(values) - min(values)
        corner_rows = [p for p in packets if p["zone"] != "Straight"]
        straight_rows = [p for p in packets if p["zone"] == "Straight"]
        self.assertGreater(spread(corner_rows), 0.25)
        self.assertLess(spread(straight_rows), spread(corner_rows))

    def test_mixed_pace_shows_every_colour(self):
        """Mixed: over five laps there are green, amber and red readings."""
        stages = {p["stage"] for p in lap_packets("mixed", seed=4, laps=5)}
        self.assertEqual(stages, {"NOMINAL", "MONITORING", "INTERVENE"})

    def test_unknown_pace_is_refused(self):
        """Only safe, edge and over are allowed."""
        with self.assertRaises(ValueError):
            ProfileSimulator(load_profile(FIXTURE), "fast")


class SeedAndVariationTests(unittest.TestCase):
    """Runs repeat with the same seed and differ lap to lap."""

    def test_same_seed_gives_identical_runs(self):
        """Two runs with seed 7 are identical; seed 8 differs."""
        self.assertEqual(lap_packets("edge", 7), lap_packets("edge", 7))
        self.assertNotEqual(lap_packets("edge", 7), lap_packets("edge", 8))

    def test_laps_differ_within_one_run(self):
        """Corner peaks vary from lap to lap by a few percent."""
        peaks = corner_peaks(lap_packets("edge", seed=4, laps=6))
        first_corner = [g for (lap, zone), (g, _) in sorted(peaks.items()) if zone == "Corner 1"]
        self.assertGreater(len(set(first_corner)), 1)
        self.assertLess(max(first_corner) / min(first_corner), 1.15)


class LapShapeTests(unittest.TestCase):
    """Zones, progress, time step and smoothness."""

    def setUp(self):
        """Load one safe lap."""
        self.packets = lap_packets("safe", seed=5, laps=1)

    def test_zone_tagging_uses_corner_names_and_straight(self):
        """Corners are named from the profile; everything else is Straight with limit 99."""
        zones = {p["zone"] for p in self.packets}
        self.assertEqual(zones, {"Straight", "Corner 1", "Corner 2", "Corner 3", "Corner 4"})
        self.assertTrue(all(p["threshold"] == (99.0 if p["zone"] == "Straight" else LIMIT) for p in self.packets))

    def test_progress_runs_from_zero_to_one_once_per_lap(self):
        """Progress never goes backwards inside a lap and starts at 0."""
        progress = [p["track_progress"] for p in self.packets]
        self.assertEqual(progress[0], 0.0)
        self.assertEqual(progress, sorted(progress))
        self.assertLess(progress[-1], 1.0)

    def test_lap_numbers_and_time_step(self):
        """Three laps are numbered 1..3 and each takes lap_length / speed seconds in 0.2 s steps."""
        packets = lap_packets("safe", seed=5, laps=3)
        self.assertEqual({p["lap"] for p in packets}, {1, 2, 3})
        self.assertEqual(TIME_STEP_S, 0.2)
        lap_seconds = len([p for p in packets if p["lap"] == 1]) * TIME_STEP_S
        self.assertGreater(lap_seconds, 20.0)
        self.assertLess(lap_seconds, 60.0)

    def test_g_does_not_jump_between_readings(self):
        """Smoothed speed keeps the change in g between neighbouring readings small."""
        g = [p["g_force"] for p in self.packets]
        self.assertLess(max(abs(b - a) for a, b in zip(g, g[1:])), 0.35)

    def test_straight_readings_are_low_and_speed_is_plausible(self):
        """On straights g is near zero and speed never exceeds the 80 km/h cruise."""
        straight = [p for p in self.packets if p["zone"] == "Straight"]
        self.assertLess(sorted(p["g_force"] for p in straight)[len(straight) // 2], 0.2)
        self.assertLessEqual(max(p["speed_kmh"] for p in self.packets), 80.1)
        self.assertGreater(min(p["speed_kmh"] for p in self.packets), 10.0)

    def test_speed_changes_are_limited(self):
        """Between readings speed changes by less than hard kart braking (about 1 g = 2 m/s in 0.2 s)."""
        speeds = [p["speed_kmh"] / 3.6 for p in self.packets]
        self.assertLess(max(abs(b - a) for a, b in zip(speeds, speeds[1:])), 2.1)

    def test_speed_profile_is_below_cruise_everywhere(self):
        """No point is faster than cruise, so g cannot exceed what the corner speeds allow."""
        simulator = ProfileSimulator(load_profile(FIXTURE), "over", seed=1)
        speeds = speed_profile(simulator.profile, simulator.curvature, simulator.member,
                               simulator.corner_radii, 1.08, simulator.cruise_ms, [1.0] * 4)
        self.assertLessEqual(max(speeds), simulator.cruise_ms + 1e-9)


class OutputTests(unittest.TestCase):
    """Readings go to the same three outputs as the built-in track, in the same formats."""

    def test_bridge_line_format_is_unchanged(self):
        """Every serial line is 'g,STAGE' with a newline, exactly as before."""
        written = []

        class FakeSerial:
            """Collects what would be written to the bridge."""

            def write(self, data):
                """Remember one line."""
                written.append(data.decode())

        simulator = ProfileSimulator(load_profile(FIXTURE), "edge", seed=1)
        with mock.patch.object(sim_profile_run, "broadcast_reading"), \
                mock.patch.object(sim_profile_run, "send_to_backend") as backend, \
                mock.patch.object(sim_profile_run.time, "sleep"):
            sim_profile_run.run_profile_lap(simulator, FakeSerial(), "session-1", 1, 1, 0.0)
        self.assertGreater(len(written), 100)
        self.assertRegex("".join(written), r"^(\d+\.\d{1,2},(NOMINAL|MONITORING|INTERVENE)\n)+$")
        self.assertEqual(backend.call_count, len(written))
        self.assertEqual(backend.call_args.kwargs["lap_number"], 1)

    def test_every_reading_is_broadcast(self):
        """The visualizer receives each packet with the keys it already expects."""
        simulator = ProfileSimulator(load_profile(FIXTURE), "safe", seed=1)
        with mock.patch.object(sim_profile_run, "broadcast_reading") as broadcast, \
                mock.patch.object(sim_profile_run, "send_to_backend"), mock.patch.object(sim_profile_run.time, "sleep"):
            sim_profile_run.run_profile_lap(simulator, None, "", 2, 2, 0.0)
        keys = {"lap", "zone", "g_force", "stage", "speed_kmh", "track_progress", "threshold"}
        self.assertTrue(broadcast.call_count > 100)
        self.assertEqual(set(broadcast.call_args.args[0]), keys)

    def test_run_start_extras_have_outline_and_labels(self):
        """Outline (at most 2,000 points) and corner labels are added to run_start."""
        simulator = ProfileSimulator(load_profile(FIXTURE), "safe", seed=1)
        extras = sim_profile_run.build_run_start_extras(simulator)
        self.assertEqual(len(extras["outline"]), 301)
        self.assertEqual([c["label"] for c in extras["corners"]], ["Corner 1", "Corner 2", "Corner 3", "Corner 4"])
        self.assertTrue(all(0 <= c["label_index"] < 301 for c in extras["corners"]))

    def test_run_start_outline_is_capped_at_2000_points(self):
        """A 5,000-point profile is thinned to at most 2,000 points with matching corner indexes."""
        simulator = ProfileSimulator(load_profile(FIXTURE), "safe", seed=1)
        big = [(i * 0.5, 0.0) for i in range(5000)]
        simulator.profile.outline = big
        extras = sim_profile_run.build_run_start_extras(simulator)
        self.assertLessEqual(len(extras["outline"]), 2000)
        self.assertTrue(all(c["label_index"] < len(extras["outline"]) for c in extras["corners"]))


if __name__ == "__main__":
    unittest.main()
