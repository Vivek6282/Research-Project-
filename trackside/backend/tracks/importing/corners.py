"""
Trackside — Find the corners on a track outline (C4).

Curvature is measured as the radius of the circle through three outline points
about 10 m apart. A corner is a continuous stretch tighter than a radius
threshold (default 60 m) that is at least 8 m long; corners closer than 10 m
are merged. The outline is a closed loop, so a corner can cross the start line.
"""

import math
from dataclasses import dataclass
from typing import List, Tuple

from tracks.importing.geometry import Point, distance
from tracks.importing.outline import Outline

DEFAULT_RADIUS_THRESHOLD_M = 60.0
MIN_RADIUS_THRESHOLD_M = 10.0
MAX_RADIUS_THRESHOLD_M = 200.0
MIN_CORNER_LENGTH_M = 8.0
MERGE_GAP_M = 10.0
TRIPLET_BASELINE_M = 10.0
NO_CURVE = math.inf
# Tightest radius is judged on curvature averaged over this many points (about 8 m),
# so one noisy GPS point cannot make a corner look tighter than it is
TIGHTEST_WINDOW = 5


@dataclass
class Corner:
    """One corner: where it starts, ends and is tightest (outline indexes), and its tightest radius."""

    start_index: int
    end_index: int
    apex_index: int
    tightest_radius_m: float
    length_m: float


def circle_radius(a: Point, b: Point, c: Point) -> float:
    """Radius (m) of the circle through three points; infinity when they are in a straight line."""
    cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    if abs(cross) < 1e-9:
        return NO_CURVE
    return distance(a, b) * distance(b, c) * distance(a, c) / (2.0 * abs(cross))


def radius_profile(points: List[Point], spacing_m: float) -> List[float]:
    """Radius at every outline point, using neighbours about 10 m behind and ahead (wrapping)."""
    n = len(points)
    offset = max(1, int(round(TRIPLET_BASELINE_M / spacing_m)))
    return [circle_radius(points[(i - offset) % n], points[i], points[(i + offset) % n]) for i in range(n)]


def find_runs(flags: List[bool]) -> List[Tuple[int, int]]:
    """List (first, last) index pairs of consecutive True flags in a plain list."""
    runs, start = [], None
    for i, flag in enumerate(flags):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            runs.append((start, i - 1))
            start = None
    if start is not None:
        runs.append((start, len(flags) - 1))
    return runs


def merge_close_runs(runs: List[Tuple[int, int]], total: int, spacing_m: float) -> List[Tuple[int, int]]:
    """Merge runs whose gap is under 10 m, including across the end of the list (the loop's seam)."""
    merged: List[Tuple[int, int]] = []
    for start, end in runs:
        if merged and (start - merged[-1][1] - 1) * spacing_m < MERGE_GAP_M:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    if len(merged) > 1:
        seam_gap = (merged[0][0] + total - merged[-1][1] - 1) * spacing_m
        if seam_gap < MERGE_GAP_M:
            last = merged.pop()
            merged[0] = (last[0], merged[0][1] + total)
    return merged


def sustained_radius(radii: List[float], index: int) -> float:
    """Radius at a point judged from the average curvature of its neighbours (wrapping)."""
    n, half = len(radii), TIGHTEST_WINDOW // 2
    curvature = sum(1.0 / radii[(index + k) % n] for k in range(-half, half + 1)) / TIGHTEST_WINDOW
    return NO_CURVE if curvature <= 0 else 1.0 / curvature


def make_corner(start: int, end: int, radii: List[float], spacing_m: float) -> Corner:
    """Describe one run (indexes may run past the end of the loop for a corner on the seam)."""
    n = len(radii)
    tightest, apex = min((sustained_radius(radii, i % n), i % n) for i in range(start, end + 1))
    return Corner(start_index=start % n, end_index=end % n, apex_index=apex,
                  tightest_radius_m=tightest, length_m=(end - start + 1) * spacing_m)


def find_corners(outline: Outline, radius_threshold_m: float = DEFAULT_RADIUS_THRESHOLD_M) -> List[Corner]:
    """Find corners tighter than the threshold, numbered in driving order from the outline start."""
    radii = radius_profile(outline.points, outline.spacing_m)
    n = len(radii)
    flags = [r < radius_threshold_m for r in radii]
    if not any(flags):
        return []
    if all(flags):
        return [make_corner(0, n - 1, radii, outline.spacing_m)]

    # Turn the loop into a straight list that begins on a non-corner point
    shift = flags.index(False) + 1
    rotated = flags[shift:] + flags[:shift]
    long_enough = [(s, e) for s, e in find_runs(rotated) if (e - s + 1) * outline.spacing_m >= MIN_CORNER_LENGTH_M]
    merged = merge_close_runs(long_enough, n, outline.spacing_m)
    corners = [make_corner(s + shift, e + shift, radii, outline.spacing_m) for s, e in merged]
    return sorted(corners, key=lambda corner: corner.apex_index)


def corner_to_json(number: int, corner: Corner, outline: Outline) -> dict:
    """The JSON for one corner: name suggestion, start/end/apex positions and tightest radius."""
    frame, points = outline.frame, outline.points

    def at(index: int) -> dict:
        """Lat/lng of an outline point."""
        lat, lng = frame.to_lat_lng(*points[index])
        return {"lat": round(lat, 7), "lng": round(lng, 7)}

    return {
        "number": number,
        "suggested_name": f"Turn {number}",
        "start": at(corner.start_index),
        "end": at(corner.end_index),
        "apex": at(corner.apex_index),
        "start_index": corner.start_index,
        "end_index": corner.end_index,
        "apex_index": corner.apex_index,
        "tightest_radius_m": round(corner.tightest_radius_m, 1),
        "length_m": round(corner.length_m, 1),
    }
