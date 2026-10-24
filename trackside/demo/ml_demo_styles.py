"""
Trackside — SYNTHETIC driving styles, corners and anomalies for the ML demo data (Phase 2.3).

Nothing here is measured from a real driver. The numbers are chosen so that the
four styles differ in plain, explainable ways (where they brake, how close to
the corner limit they run, how consistent they are), which is what the
driving-style badges (clustering) and the anomaly flags need to be demonstrated.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class DrivingStyle:
    """How one kind of driver behaves in every corner (means and spreads)."""

    name: str
    brake_point_mean_m: float      # distance before the apex where braking starts
    brake_point_spread_m: float    # lap-to-lap spread of that distance
    grip_use_mean: float           # peak lateral g as a fraction of the corner limit
    grip_use_spread: float
    improvement_per_session: float  # fraction of corner time gained per session (learning)


@dataclass(frozen=True)
class Corner:
    """One corner of the synthetic track."""

    label: str
    limit_g: float          # the corner limit the stage rule uses
    base_time_s: float      # time through the corner for a neutral driver
    base_entry_kmh: float   # entry speed for a neutral driver


STYLES: Dict[str, DrivingStyle] = {
    "smooth_early_braker": DrivingStyle("smooth_early_braker", 46.0, 2.0, 0.76, 0.025, 0.002),
    "late_braker_aggressive": DrivingStyle("late_braker_aggressive", 28.0, 3.0, 0.95, 0.040, 0.002),
    "inconsistent_learner": DrivingStyle("inconsistent_learner", 38.0, 8.0, 0.84, 0.090, 0.006),
    "consistent_fast": DrivingStyle("consistent_fast", 35.0, 1.5, 0.90, 0.020, 0.001),
}

CORNERS: List[Corner] = [
    Corner("Turn 1", 1.30, 3.2, 72.0),
    Corner("Turn 2", 1.20, 2.6, 64.0),
    Corner("Hairpin", 1.10, 4.8, 48.0),
    Corner("Turn 4", 1.25, 2.9, 68.0),
    Corner("Chicane", 1.15, 3.6, 55.0),
]

# Neutral reference the corner-time model compares against
NEUTRAL_BRAKE_POINT_M = 36.0
NEUTRAL_GRIP_USE = 0.85

# Injected anomalies: what goes wrong and how it shows in the numbers
ANOMALY_KINDS = {
    # locked the brakes: very late braking, grip spike over the limit, big time loss
    "lockup": {"brake_shift_m": -14.0, "grip_shift": 0.22, "time_factor": 1.18},
    # ran wide / off the line: little grip used, large time loss
    "off_line": {"brake_shift_m": 0.0, "grip_shift": -0.25, "time_factor": 1.28},
    # missed the apex: braked far too early, moderate time loss
    "missed_apex": {"brake_shift_m": 16.0, "grip_shift": -0.12, "time_factor": 1.14},
}
ANOMALY_RATE = 0.02   # share of corner passes that get an anomaly

# Two drivers per style, with obviously made-up names
DRIVERS = [
    ("SYN-01", "Synthetic Driver A", "smooth_early_braker"),
    ("SYN-02", "Synthetic Driver B", "smooth_early_braker"),
    ("SYN-03", "Synthetic Driver C", "late_braker_aggressive"),
    ("SYN-04", "Synthetic Driver D", "late_braker_aggressive"),
    ("SYN-05", "Synthetic Driver E", "inconsistent_learner"),
    ("SYN-06", "Synthetic Driver F", "inconsistent_learner"),
    ("SYN-07", "Synthetic Driver G", "consistent_fast"),
    ("SYN-08", "Synthetic Driver H", "consistent_fast"),
]
