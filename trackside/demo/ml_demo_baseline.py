"""
Trackside — Simple baselines on the SYNTHETIC ML demo data (Phase 2.3).

Shows that the demo data can demonstrate both features, using plain Python only:
  1. Driving-style badges: k-means on each driver's summary numbers (4 groups).
  2. Anomaly flags: a corner pass is unusual when its braking point, grip use or
     time is far from that driver's own history in that corner (robust z-score:
     median and median absolute deviation). Time is first divided by the
     driver's median time in that corner and session, so getting faster over the
     weeks (learning) is not mistaken for an anomaly.

    py ml_demo_baseline.py            # generates the data in memory and prints the results

These are baselines to compare a real model against, not the model itself.
"""

import random
from statistics import mean, median, pstdev
from typing import Dict, List, Tuple

from ml_demo_data import DEFAULT_SEED, driver_features, generate_corner_rows

CLUSTER_FEATURES = ["mean_brake_point_m", "brake_point_spread_m", "mean_grip_use", "grip_use_spread"]
ANOMALY_FEATURES = ["relative_time", "brake_point_m", "grip_use"]
ANOMALY_Z_LIMIT = 4.0
MAD_TO_SIGMA = 1.4826   # turns a median absolute deviation into a standard-deviation-sized number


def standardise(rows: List[dict], columns: List[str]) -> List[List[float]]:
    """Each column rescaled to mean 0 and spread 1, so no single unit dominates the distances."""
    scaled_columns = []
    for column in columns:
        values = [row[column] for row in rows]
        centre, spread = mean(values), pstdev(values) or 1.0
        scaled_columns.append([(value - centre) / spread for value in values])
    return [list(point) for point in zip(*scaled_columns)]


def squared_distance(first: List[float], second: List[float]) -> float:
    """Squared straight-line distance between two points."""
    return sum((a - b) ** 2 for a, b in zip(first, second))


def k_means(points: List[List[float]], groups: int, seed: int = DEFAULT_SEED, rounds: int = 50) -> List[int]:
    """Group number for every point (classic k-means with a fixed seed, best of 10 starts)."""
    rng = random.Random(seed)
    best_labels, best_spread = [], float("inf")
    for _ in range(10):
        centres = [list(point) for point in rng.sample(points, groups)]
        labels = [0] * len(points)
        for _ in range(rounds):
            labels = [min(range(groups), key=lambda g: squared_distance(p, centres[g])) for p in points]
            for group in range(groups):
                members = [p for p, label in zip(points, labels) if label == group]
                if members:
                    centres[group] = [mean(values) for values in zip(*members)]
        spread = sum(squared_distance(p, centres[label]) for p, label in zip(points, labels))
        if spread < best_spread:
            best_labels, best_spread = labels, spread
    return best_labels


def style_badges(features: List[dict]) -> Dict[str, int]:
    """{driver_id: group number} from k-means with 4 groups."""
    labels = k_means(standardise(features, CLUSTER_FEATURES), groups=4)
    return {row["driver_id"]: label for row, label in zip(features, labels)}


def robust_z_scores(values: List[float]) -> List[float]:
    """How unusual each value is next to the others (median-based, so one odd value cannot hide itself)."""
    centre = median(values)
    spread = median(abs(value - centre) for value in values) * MAD_TO_SIGMA or 1e-9
    return [(value - centre) / spread for value in values]


def relative_times(rows: List[dict]) -> List[float]:
    """Each corner time divided by the driver's median time in that corner and session."""
    session_times: Dict[Tuple, List[float]] = {}
    for row in rows:
        session_times.setdefault((row["driver_id"], row["corner"], row["session_number"]), []).append(row["corner_time_s"])
    session_median = {key: median(times) for key, times in session_times.items()}
    return [row["corner_time_s"] / session_median[(row["driver_id"], row["corner"], row["session_number"])]
            for row in rows]


def flag_anomalies(rows: List[dict]) -> List[bool]:
    """True for each corner pass that is unusual for that driver in that corner."""
    values = {"relative_time": relative_times(rows),
              "brake_point_m": [row["brake_point_m"] for row in rows],
              "grip_use": [row["grip_use"] for row in rows]}
    groups: Dict[Tuple, List[int]] = {}
    for index, row in enumerate(rows):
        groups.setdefault((row["driver_id"], row["corner"]), []).append(index)
    flags = [False] * len(rows)
    for indexes in groups.values():
        for column in ANOMALY_FEATURES:
            for index, z_score in zip(indexes, robust_z_scores([values[column][i] for i in indexes])):
                if abs(z_score) > ANOMALY_Z_LIMIT:
                    flags[index] = True
    return flags


def precision_recall(rows: List[dict], flags: List[bool]) -> Tuple[float, float]:
    """(share of flags that were real anomalies, share of real anomalies that were flagged)."""
    flagged_true = sum(1 for row, flag in zip(rows, flags) if flag and row["true_anomaly"])
    flagged = sum(flags)
    real = sum(row["true_anomaly"] for row in rows)
    return (flagged_true / flagged if flagged else 0.0), (flagged_true / real if real else 0.0)


def main() -> None:
    """Run both baselines on freshly generated demo data and print what they found."""
    rows = generate_corner_rows()
    features = driver_features(rows)
    badges = style_badges(features)
    print("Driving-style groups (k-means, 4 groups) - SYNTHETIC data:")
    for row in features:
        print(f"  {row['driver_id']}  group {badges[row['driver_id']]}  (made-up style: {row['true_style']})")
    precision, recall = precision_recall(rows, flag_anomalies(rows))
    print(f"Anomaly flags: precision {precision:.2f}, recall {recall:.2f} "
          f"on {sum(r['true_anomaly'] for r in rows)} injected anomalies in {len(rows)} corner passes")


if __name__ == "__main__":
    main()
