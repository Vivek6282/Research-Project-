"""
Unit tests for the simulator's GPS points (Prompt 13, L2).
"""

import json
import os
import sys
import tempfile
import unittest

demo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if demo_dir not in sys.path:
    sys.path.insert(0, demo_dir)

from sim_backend_poster import build_telemetry_payload
from sim_gps import GpsLoadError, gps_for_reading, load_gps_file
from sim_physics import ProfileSimulator
from sim_profile import ProfileLoadError, load_profile

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "synthetic_profile.json")


class GpsFileTests(unittest.TestCase):
    """The GPS file is checked strictly and each reading gets an evenly spread point."""

    def write(self, data):
        """Write data as JSON to a temp file and return its path."""
        handle, path = tempfile.mkstemp(suffix=".gps.json")
        with os.fdopen(handle, "w") as out:
            json.dump(data, out)
        self.addCleanup(os.remove, path)
        return path

    def test_good_file_loads(self):
        """A version 1 file with [lat, lng] pairs loads as tuples."""
        points = load_gps_file(self.write({"version": 1, "points": [[10.0, 76.0], [10.1, 76.1]]}))
        self.assertEqual(points, [(10.0, 76.0), (10.1, 76.1)])

    def test_bad_files_are_refused(self):
        """Wrong version, bad coordinates, a missing file and too few points all raise."""
        for bad in ({"version": 2, "points": [[1, 1], [2, 2]]}, {"version": 1, "points": [[95, 1], [2, 2]]},
                    {"version": 1, "points": [[1, "x"], [2, 2]]}, {"version": 1, "points": [[1, 1]]}):
            with self.assertRaises(GpsLoadError):
                load_gps_file(self.write(bad))
        with self.assertRaises(GpsLoadError):
            load_gps_file("/no/such/file.gps.json")

    def test_48_readings_are_spread_evenly_over_the_outline(self):
        """Readings spread over the outline; the first and the last reading of a lap are both on the start/finish line."""
        points = [(float(i), 0.0) for i in range(400)]
        self.assertEqual(gps_for_reading(points, 0, 48), (0.0, 0.0))
        self.assertEqual(gps_for_reading(points, 24, 48), (204.0, 0.0))
        self.assertEqual(gps_for_reading(points, 46, 48), (391.0, 0.0))
        self.assertEqual(gps_for_reading(points, 47, 48), (0.0, 0.0))
        self.assertEqual(gps_for_reading(points, 48, 48), (0.0, 0.0))
        self.assertIsNone(gps_for_reading(None, 3, 48))


class PayloadAndProfileTests(unittest.TestCase):
    """GPS reaches the payload; nothing else in it changes."""

    def test_payload_carries_gps_and_defaults_to_zero(self):
        """With a point the payload has it; without one it is 0.0 / 0.0 as before."""
        with_gps = build_telemetry_payload(1.0, 50, "Hairpin", 1, recorded_at="2026-01-01T00:00:00Z", gps=(10.5, 76.25))
        without = build_telemetry_payload(1.0, 50, "Hairpin", 1, recorded_at="2026-01-01T00:00:00Z")
        self.assertEqual((with_gps["gps_lat"], with_gps["gps_lng"]), (10.5, 76.25))
        self.assertEqual((without["gps_lat"], without["gps_lng"]), (0.0, 0.0))
        self.assertEqual({k: v for k, v in with_gps.items() if k not in ("gps_lat", "gps_lng")},
                         {k: v for k, v in without.items() if k not in ("gps_lat", "gps_lng")})

    def test_profile_without_gps_gives_none_and_packets_have_no_gps_keys(self):
        """The fixture has no gps list: current_gps is None; broadcast packets never carry gps."""
        simulator = ProfileSimulator(load_profile(FIXTURE), "safe", seed=1)
        packet = next(simulator.lap_packets(1))
        self.assertIsNone(simulator.current_gps())
        self.assertFalse([k for k in packet if "gps" in k or "lat" in k.lower()])

    def test_profile_gps_follows_the_outline_index(self):
        """With a gps list, current_gps is the point of the outline index the latest packet is on."""
        profile = load_profile(FIXTURE)
        profile.gps = [(10.0 + i * 1e-5, 76.0) for i in range(len(profile.outline))]
        simulator = ProfileSimulator(profile, "safe", seed=1)
        for _ in zip(range(30), simulator.lap_packets(1)):
            self.assertEqual(simulator.current_gps(), profile.gps[simulator.current_index])
        self.assertGreater(simulator.current_index, 0)

    def test_profile_gps_of_wrong_length_is_refused(self):
        """A gps list that does not match the outline is a load error."""
        with open(FIXTURE, encoding="utf-8") as handle:
            data = json.load(handle)
        data["gps"] = [[10.0, 76.0]] * 3
        handle, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(handle, "w") as out:
            json.dump(data, out)
        self.addCleanup(os.remove, path)
        with self.assertRaises(ProfileLoadError):
            load_profile(path)
