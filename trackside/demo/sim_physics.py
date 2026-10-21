"""
Trackside Virtual Lap Simulator — Physics for a custom track profile (SIM-2, SIM-3).

Lateral g = v^2 x curvature / 9.81 along the outline. Straights run at a cruise
speed; each corner runs at a "pace" fraction of its safe speed, where
safe speed = sqrt(limit x 9.81 x tightest radius). Speeds change smoothly (limited
acceleration and braking), so g never jumps. Everything here is pure maths: no
network, no serial, no clock.
"""

import math
import random
from typing import Dict, List, Optional, Tuple

from sim_profile import ProfileCorner, TrackProfile
from sim_track import classify_stage

GRAVITY = 9.81
TIME_STEP_S = 0.2
DEFAULT_CRUISE_KMH = 80.0
# Pace = fraction of each corner's safe speed. At the tightest point g = pace^2 x limit,
# so safe stays green (0.72), edge is amber (0.96) and over is red (1.17).
PACES: Dict[str, float] = {"safe": 0.85, "edge": 0.98, "over": 1.08}
# Lap-to-lap variation: each corner's lateral g is scaled by 1 +/- 3% (speed by about 1.5%),
# so laps differ but "edge" can never tip into red by chance
VARIATION = 0.03
ACCEL_MS2 = 3.5
BRAKE_MS2 = 6.0
# Bends nobody marked as a corner are driven at no more than this lateral g
UNMARKED_BEND_MAX_G = 0.9
# Same measuring rule as the importer: circle through points about 10 m apart,
# curvature averaged over 5 points
TRIPLET_BASELINE_M = 10.0
CURVATURE_WINDOW = 5
STRAIGHT_THRESHOLD_G = 99.0
READING_NOISE_G = 0.01
MIN_READING_G = 0.05

Point = Tuple[float, float]


def circle_curvature(a: Point, b: Point, c: Point) -> float:
    """Curvature (1 / radius, in 1/m) of the circle through three points; 0 for a straight line."""
    cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    side_ab, side_bc, side_ac = math.dist(a, b), math.dist(b, c), math.dist(a, c)
    if abs(cross) < 1e-9 or side_ab * side_bc * side_ac < 1e-12:
        return 0.0
    return 2.0 * abs(cross) / (side_ab * side_bc * side_ac)


def curvature_profile(points: List[Point], spacing_m: float) -> List[float]:
    """Curvature at every outline point: triplet curvature averaged over a 5-point window (wrapping)."""
    count = len(points)
    offset = max(1, int(round(TRIPLET_BASELINE_M / spacing_m)))
    raw = [circle_curvature(points[(i - offset) % count], points[i], points[(i + offset) % count]) for i in range(count)]
    half = CURVATURE_WINDOW // 2
    return [sum(raw[(i + k) % count] for k in range(-half, half + 1)) / CURVATURE_WINDOW for i in range(count)]


def corner_indexes(corner: ProfileCorner, count: int) -> List[int]:
    """Outline indexes of a corner, from start to end driving forward round the loop."""
    indexes, i = [corner.start_index], corner.start_index
    while i != corner.end_index and len(indexes) <= count:
        i = (i + 1) % count
        indexes.append(i)
    return indexes


def corner_membership(profile: TrackProfile) -> List[Optional[int]]:
    """For each outline point, the number of the corner it belongs to, or None on a straight."""
    count = len(profile.outline)
    member: List[Optional[int]] = [None] * count
    for number, corner in enumerate(profile.corners):
        for i in corner_indexes(corner, count):
            if member[i] is None:
                member[i] = number
    return member


def tightest_radius(profile: TrackProfile, curvature: List[float]) -> List[float]:
    """Tightest radius (m) of each corner, measured on this outline with the same rule as the speed."""
    count = len(profile.outline)
    radii = []
    for corner in profile.corners:
        peak = max(curvature[i] for i in corner_indexes(corner, count))
        radii.append(1.0 / peak if peak > 0 else corner.tightest_radius_m)
    return radii


def safe_speed_ms(limit_g: float, radius_m: float) -> float:
    """Fastest speed (m/s) that keeps lateral g at the limit: sqrt(limit x 9.81 x radius)."""
    return math.sqrt(limit_g * GRAVITY * radius_m)


def smooth_speeds(targets: List[float], spacing_m: float) -> List[float]:
    """Limit braking and acceleration so speed changes smoothly all the way round the loop."""
    speeds, count = list(targets), len(targets)
    for _ in range(2):
        for i in reversed(range(count)):
            ahead = speeds[(i + 1) % count]
            speeds[i] = min(speeds[i], math.sqrt(ahead * ahead + 2.0 * BRAKE_MS2 * spacing_m))
        for i in range(count):
            behind = speeds[(i - 1) % count]
            speeds[i] = min(speeds[i], math.sqrt(behind * behind + 2.0 * ACCEL_MS2 * spacing_m))
    return speeds


def speed_profile(profile: TrackProfile, curvature: List[float], member: List[Optional[int]],
                  corner_radii: List[float], pace: float, cruise_ms: float, g_scales: List[float]) -> List[float]:
    """Speed (m/s) at every outline point for one lap, given the pace and each corner's g scale."""
    targets = []
    for i, kappa in enumerate(curvature):
        number = member[i]
        if number is not None:
            corner = profile.corners[number]
            speed = pace * math.sqrt(g_scales[number]) * safe_speed_ms(corner.threshold_g, corner_radii[number])
        elif kappa > 1e-9:
            speed = min(cruise_ms, math.sqrt(UNMARKED_BEND_MAX_G * GRAVITY / kappa))
        else:
            speed = cruise_ms
        targets.append(min(speed, cruise_ms))
    return smooth_speeds(targets, profile.spacing_m)


class ProfileSimulator:
    """Produces the telemetry packets of one lap at a time for a track profile."""

    def __init__(self, profile: TrackProfile, pace_name: str = "safe",
                 cruise_kmh: float = DEFAULT_CRUISE_KMH, seed: Optional[int] = None):
        """Prepare curvature, corner membership and the random source (a seed makes runs repeatable)."""
        if pace_name not in PACES:
            raise ValueError(f"pace must be one of {sorted(PACES)}")
        self.profile = profile
        self.pace = PACES[pace_name]
        self.cruise_ms = cruise_kmh / 3.6
        self.rng = random.Random(seed)
        self.curvature = curvature_profile(profile.outline, profile.spacing_m)
        self.member = corner_membership(profile)
        self.corner_radii = tightest_radius(profile, self.curvature)
        self.total_m = profile.spacing_m * len(profile.outline)

    def lap_packets(self, lap_number: int):
        """Yield one telemetry packet every 0.2 s of simulated time for a full lap."""
        scales = [1.0 + self.rng.uniform(-VARIATION, VARIATION) for _ in self.profile.corners]
        speeds = speed_profile(self.profile, self.curvature, self.member, self.corner_radii,
                               self.pace, self.cruise_ms, scales)
        distance_m = 0.0
        while distance_m < self.total_m:
            i = min(int(distance_m / self.profile.spacing_m), len(speeds) - 1)
            speed = speeds[i]
            number = self.member[i]
            corner = self.profile.corners[number] if number is not None else None
            lateral_g = speed * speed * self.curvature[i] / GRAVITY
            lateral_g = max(MIN_READING_G, lateral_g + self.rng.uniform(-READING_NOISE_G, READING_NOISE_G))
            threshold = corner.threshold_g if corner else STRAIGHT_THRESHOLD_G
            yield {
                "lap": lap_number,
                "zone": corner.label if corner else "Straight",
                "g_force": round(lateral_g, 2),
                "stage": classify_stage(lateral_g, threshold),
                "speed_kmh": round(speed * 3.6, 1),
                "track_progress": round(distance_m / self.total_m, 4),
                "threshold": threshold,
            }
            distance_m += speed * TIME_STEP_S
