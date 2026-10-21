"""
Unit tests for the simulator's track profile loader (SIM-1).
"""

import json
import os
import sys
import tempfile
import unittest

demo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if demo_dir not in sys.path:
    sys.path.insert(0, demo_dir)

from sim_profile import ProfileLoadError, load_profile


def good_profile():
    """A small valid profile: a 30-point outline and one corner."""
    return {
        "version": 1, "track_id": "t", "name": "Test", "spacing_m": 2.0, "length_m": 60.0,
        "outline": [[float(i), float(i % 5)] for i in range(30)],
        "corners": [{"label": "Turn 1", "start_index": 3, "end_index": 9, "tightest_radius_m": 20.0, "threshold_g": 1.2}],
    }


class SimProfileTests(unittest.TestCase):
    """load_profile accepts good files and rejects every kind of bad one."""

    def write(self, data, raw=None):
        """Write a profile to a temp file and return its path."""
        handle, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(handle, "w") as out:
            out.write(raw if raw is not None else json.dumps(data))
        self.addCleanup(os.remove, path)
        return path

    def test_good_profile_loads(self):
        """Name, outline, corner values and spacing come through."""
        profile = load_profile(self.write(good_profile()))
        self.assertEqual((profile.name, len(profile.outline), len(profile.corners)), ("Test", 30, 1))
        self.assertEqual(profile.corners[0].tightest_radius_m, 20.0)

    def test_missing_and_broken_files_are_refused(self):
        """A missing path, invalid JSON and a wrong version give ProfileLoadError."""
        with self.assertRaises(ProfileLoadError):
            load_profile("/nonexistent/profile.json")
        with self.assertRaises(ProfileLoadError):
            load_profile(self.write(None, raw="{not json"))
        bad = good_profile()
        bad["version"] = 2
        with self.assertRaises(ProfileLoadError):
            load_profile(self.write(bad))

    def test_bad_values_are_refused(self):
        """NaN, a corner outside the outline, a reserved or duplicate name, and tiny outlines fail."""
        cases = []
        nan = good_profile(); nan["outline"][0] = [float("nan"), 0.0]; cases.append(nan)
        outside = good_profile(); outside["corners"][0]["end_index"] = 99; cases.append(outside)
        reserved = good_profile(); reserved["corners"][0]["label"] = "Straight"; cases.append(reserved)
        dup = good_profile(); dup["corners"].append(dict(dup["corners"][0], label="turn 1")); cases.append(dup)
        tiny = good_profile(); tiny["outline"] = tiny["outline"][:5]; cases.append(tiny)
        radius = good_profile(); radius["corners"][0]["tightest_radius_m"] = 0; cases.append(radius)
        limit = good_profile(); limit["corners"][0]["threshold_g"] = "1.2"; cases.append(limit)
        for case in cases:
            with self.assertRaises(ProfileLoadError, msg=str(case)[:80]):
                load_profile(self.write(case))


if __name__ == "__main__":
    unittest.main()
