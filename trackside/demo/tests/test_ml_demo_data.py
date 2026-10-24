"""
Tests for the SYNTHETIC ML demo data and its baselines (Phase 2.3).
"""

import csv
import os
import sys
import tempfile
import unittest

demo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if demo_dir not in sys.path:
    sys.path.insert(0, demo_dir)

import ml_demo_baseline
import ml_demo_data
from ml_demo_styles import CORNERS, DRIVERS


class TestGeneratedData(unittest.TestCase):
    """Shape, ranges, labels and repeatability of the generated rows."""

    @classmethod
    def setUpClass(cls):
        """Generate the default data set once."""
        cls.rows = ml_demo_data.generate_corner_rows()

    def test_one_row_per_driver_session_lap_and_corner(self):
        """8 drivers x 12 sessions x 10 laps x 5 corners."""
        expected = len(DRIVERS) * ml_demo_data.SESSIONS_PER_DRIVER * ml_demo_data.LAPS_PER_SESSION * len(CORNERS)
        self.assertEqual(len(self.rows), expected)

    def test_same_seed_same_data_other_seed_other_data(self):
        """Repeatable for a report; a different seed really changes it."""
        self.assertEqual(ml_demo_data.generate_corner_rows(), self.rows)
        self.assertNotEqual(ml_demo_data.generate_corner_rows(seed=1), self.rows)

    def test_values_stay_in_believable_ranges(self):
        """Braking point, grip use, peak g and corner time are all physically sensible."""
        for row in self.rows:
            self.assertGreaterEqual(row["brake_point_m"], 5.0)
            self.assertTrue(0.30 <= row["grip_use"] <= 1.40)
            self.assertAlmostEqual(row["peak_lateral_g"], row["grip_use"] * row["corner_limit_g"], places=2)
            self.assertTrue(1.0 < row["corner_time_s"] < 10.0)

    def test_about_two_percent_anomalies_each_with_a_kind(self):
        """Injected anomalies are rare and always say what kind they are."""
        anomalies = [row for row in self.rows if row["true_anomaly"]]
        self.assertTrue(0.01 < len(anomalies) / len(self.rows) < 0.03)
        self.assertTrue(all(row["anomaly_kind"] for row in anomalies))
        self.assertFalse(any(row["anomaly_kind"] for row in self.rows if not row["true_anomaly"]))

    def test_written_files_are_marked_synthetic(self):
        """Both CSV files start with the SYNTHETIC warning and use made-up driver names."""
        with tempfile.TemporaryDirectory() as folder:
            ml_demo_data.main(["--out", folder])
            for name in ("corner_passes.csv", "driver_features.csv"):
                with open(os.path.join(folder, name), encoding="utf-8") as handle:
                    self.assertTrue(handle.readline().startswith("# SYNTHETIC DEMO DATA"))
                    names = {row["driver_name"] for row in csv.DictReader(handle)}
                self.assertTrue(all(n.startswith("Synthetic Driver") for n in names))


class TestBaselinesCanDemonstrateTheFeatures(unittest.TestCase):
    """The data is good enough to show both ML features working."""

    def test_k_means_puts_each_pair_of_same_style_drivers_together(self):
        """4 groups, and the two drivers of each style share a group."""
        features = ml_demo_data.driver_features(ml_demo_data.generate_corner_rows())
        badges = ml_demo_baseline.style_badges(features)
        style_groups = {}
        for row in features:
            style_groups.setdefault(row["true_style"], set()).add(badges[row["driver_id"]])
        self.assertTrue(all(len(groups) == 1 for groups in style_groups.values()))
        self.assertEqual(len({next(iter(g)) for g in style_groups.values()}), 4)

    def test_anomaly_flags_find_most_injected_anomalies_with_few_false_flags(self):
        """Recall and precision both at least 0.85 on the default data."""
        rows = ml_demo_data.generate_corner_rows()
        precision, recall = ml_demo_baseline.precision_recall(rows, ml_demo_baseline.flag_anomalies(rows))
        self.assertGreaterEqual(recall, 0.85)
        self.assertGreaterEqual(precision, 0.85)

    def test_learning_over_the_weeks_is_not_flagged(self):
        """The fast learner's normal passes in their last session are not flagged for being quicker."""
        rows = ml_demo_data.generate_corner_rows()
        flags = ml_demo_baseline.flag_anomalies(rows)
        last = [flag for row, flag in zip(rows, flags) if row["driver_id"] == "SYN-05"
                and row["session_number"] == ml_demo_data.SESSIONS_PER_DRIVER and not row["true_anomaly"]]
        self.assertLessEqual(sum(last), 2)


if __name__ == "__main__":
    unittest.main()
