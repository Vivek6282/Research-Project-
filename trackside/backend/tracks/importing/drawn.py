"""
Trackside — A track drawn by clicking on a map.

The clicked points are checked, joined into a smooth closed curve (a centripetal Catmull-Rom spline, which does
not overshoot between unevenly spaced clicks), then spaced evenly and lightly smoothed exactly like an imported
lap. The result is the same Outline the corner finder, the corner editor and the saver already use.
"""

import math
from typing import List

from tracks.importing.errors import TrackImportError
from tracks.importing.geometry import LocalFrame, Point, distance, path_length, resample_closed, smooth_closed
from tracks.importing.outline import MAX_OUTLINE_POINTS, TARGET_SPACING_M, Outline
from tracks.importing.samples import GpsSample, ParsedTrackFile, is_real_position

SOURCE_DRAWN = "drawn"
MIN_POINTS = 8             # fewest clicked points that can make a track
MAX_POINTS = 1000
MIN_POINT_GAP_M = 1.0      # a click closer than this to the one before is the same click
MIN_LOOP_M = 100.0
MAX_LOOP_M = 20_000.0
MAX_RADIUS_FROM_CENTRE_M = 15_000.0
CURVE_STEP_M = 1.0         # spacing of the curve before it is evened out


def read_number(value):
    """A finite number from a JSON value (booleans and text are refused), or None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def parse_drawn_points(raw) -> ParsedTrackFile:
    """Check the clicked points and return them as GPS samples; raises TrackImportError with a clear message."""
    if not isinstance(raw, list) or not (MIN_POINTS <= len(raw) <= MAX_POINTS):
        raise TrackImportError(f"Click {MIN_POINTS} to {MAX_POINTS} points around the track.")
    samples: List[GpsSample] = []
    for item in raw:
        lat = read_number(item.get("lat")) if isinstance(item, dict) else None
        lng = read_number(item.get("lng")) if isinstance(item, dict) else None
        if not is_real_position(lat, lng):
            raise TrackImportError("Every point needs a real latitude and longitude.")
        samples.append(GpsSample(lat=lat, lng=lng))
    frame = LocalFrame(sum(s.lat for s in samples) / len(samples), sum(s.lng for s in samples) / len(samples))
    kept: List[GpsSample] = []
    for sample in samples:
        if not kept or distance(frame.to_xy(sample.lat, sample.lng), frame.to_xy(kept[-1].lat, kept[-1].lng)) >= MIN_POINT_GAP_M:
            kept.append(sample)
    if len(kept) > 1 and distance(frame.to_xy(kept[0].lat, kept[0].lng), frame.to_xy(kept[-1].lat, kept[-1].lng)) < MIN_POINT_GAP_M:
        kept.pop()   # the last click on the first point only closes the loop
    if len(kept) < MIN_POINTS:
        raise TrackImportError(f"At least {MIN_POINTS} different points are needed (some clicks were on top of each other).")
    xy = [frame.to_xy(s.lat, s.lng) for s in kept]
    if max(math.hypot(x, y) for x, y in xy) > MAX_RADIUS_FROM_CENTRE_M:
        raise TrackImportError("The points are spread over too large an area for one track.")
    loop = path_length(xy + [xy[0]])
    if not (MIN_LOOP_M <= loop <= MAX_LOOP_M):
        raise TrackImportError(f"The track must be between {MIN_LOOP_M:.0f} m and {MAX_LOOP_M / 1000:.0f} km long (it is {loop:.0f} m).")
    return ParsedTrackFile(source=SOURCE_DRAWN, samples=kept, rows_total=len(raw), rows_rejected=len(raw) - len(kept))


def curve_through(p0: Point, p1: Point, p2: Point, p3: Point, steps: int) -> List[Point]:
    """Points on the centripetal Catmull-Rom curve from p1 to p2 (p2 itself excluded), p0 and p3 shape the ends."""
    t0 = 0.0
    t1 = t0 + math.sqrt(distance(p0, p1))
    t2 = t1 + math.sqrt(distance(p1, p2))
    t3 = t2 + math.sqrt(distance(p2, p3))

    def mix(a: Point, b: Point, ta: float, tb: float, t: float) -> Point:
        """Blend a and b by where t sits between ta and tb."""
        wa, wb = (tb - t) / (tb - ta), (t - ta) / (tb - ta)
        return (wa * a[0] + wb * b[0], wa * a[1] + wb * b[1])

    result = []
    for step in range(steps):
        t = t1 + (t2 - t1) * step / steps
        a1, a2, a3 = mix(p0, p1, t0, t1, t), mix(p1, p2, t1, t2, t), mix(p2, p3, t2, t3, t)
        b1, b2 = mix(a1, a2, t0, t2, t), mix(a2, a3, t1, t3, t)
        result.append(mix(b1, b2, t1, t2, t))
    return result


def build_drawn_outline(samples: List[GpsSample]) -> Outline:
    """Turn the clicked points into one smooth closed outline (even spacing, at most 2,000 points)."""
    frame = LocalFrame(sum(s.lat for s in samples) / len(samples), sum(s.lng for s in samples) / len(samples))
    pts = [frame.to_xy(s.lat, s.lng) for s in samples]
    count = len(pts)
    dense: List[Point] = []
    for i in range(count):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % count], pts[(i + 2) % count]
        dense.extend(curve_through(p0, p1, p2, p3, max(2, math.ceil(distance(p1, p2) / CURVE_STEP_M))))
    loop_length = path_length(dense + [dense[0]])
    wanted_spacing = max(TARGET_SPACING_M, loop_length / MAX_OUTLINE_POINTS)
    wanted_count = max(int(round(loop_length / wanted_spacing)), 8)
    even = resample_closed(dense, wanted_count)
    return Outline(frame=frame, points=smooth_closed(even), spacing_m=loop_length / wanted_count)
