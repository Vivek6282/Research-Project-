"""Trackside — Small flat-earth geometry helpers (metres) for track outlines."""

import math
from typing import List, Tuple

METERS_PER_DEG_LAT = 111_194.9
Point = Tuple[float, float]


class LocalFrame:
    """Converts lat/lng to local metres (x east, y north) around a fixed origin and back."""

    def __init__(self, origin_lat: float, origin_lng: float):
        """Remember the origin and how many metres one degree of longitude is there."""
        self.origin_lat = origin_lat
        self.origin_lng = origin_lng
        self.meters_per_deg_lng = METERS_PER_DEG_LAT * math.cos(math.radians(origin_lat))

    def to_xy(self, lat: float, lng: float) -> Point:
        """Latitude/longitude to local metres."""
        return ((lng - self.origin_lng) * self.meters_per_deg_lng,
                (lat - self.origin_lat) * METERS_PER_DEG_LAT)

    def to_lat_lng(self, x: float, y: float) -> Tuple[float, float]:
        """Local metres to latitude/longitude."""
        return (self.origin_lat + y / METERS_PER_DEG_LAT,
                self.origin_lng + x / self.meters_per_deg_lng)


def distance(a: Point, b: Point) -> float:
    """Straight-line distance in metres between two points."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def path_length(points: List[Point]) -> float:
    """Total length of a polyline in metres."""
    return sum(distance(points[i], points[i + 1]) for i in range(len(points) - 1))


def point_at_distance(points: List[Point], cumulative: List[float], target: float, start: int) -> Tuple[Point, int]:
    """Interpolate the point `target` metres along the line, resuming the scan at index `start`."""
    i = start
    while i < len(points) - 2 and cumulative[i + 1] < target:
        i += 1
    span = cumulative[i + 1] - cumulative[i]
    ratio = 0.0 if span <= 0 else (target - cumulative[i]) / span
    ratio = min(max(ratio, 0.0), 1.0)
    return (points[i][0] + ratio * (points[i + 1][0] - points[i][0]),
            points[i][1] + ratio * (points[i + 1][1] - points[i][1])), i


def resample_closed(points: List[Point], count: int) -> List[Point]:
    """Return `count` points spaced equally around a closed loop (last point joins back to the first)."""
    loop = points + [points[0]]
    cumulative = [0.0]
    for i in range(1, len(loop)):
        cumulative.append(cumulative[-1] + distance(loop[i - 1], loop[i]))
    step = cumulative[-1] / count
    result, index = [], 0
    for n in range(count):
        point, index = point_at_distance(loop, cumulative, n * step, index)
        result.append(point)
    return result


def smooth_closed(points: List[Point], half_window: int = 2) -> List[Point]:
    """Triangular moving average over a closed loop (the ends wrap around)."""
    n = len(points)
    weights = [half_window + 1 - abs(k) for k in range(-half_window, half_window + 1)]
    total_weight = sum(weights)
    smoothed = []
    for i in range(n):
        x = sum(w * points[(i + k) % n][0] for w, k in zip(weights, range(-half_window, half_window + 1)))
        y = sum(w * points[(i + k) % n][1] for w, k in zip(weights, range(-half_window, half_window + 1)))
        smoothed.append((x / total_weight, y / total_weight))
    return smoothed
