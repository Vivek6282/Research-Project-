"""
Trackside — Schematic outline of the built-in Demo Circuit.

ASSUMPTION: the Demo Circuit has no surveyed GPS outline. This outline is the
track shape the live visualizer already DRAWS (its SVG path, 700 x 450 view units),
sampled along its length, flipped so north is up, and scaled so one lap is about
800 m. It is a schematic picture, not a real survey, and is labelled that way in
the UI. It is used only for thumbnails and for "Duplicate as custom map"; it does
NOT change how the built-in map is simulated.

Corner positions come from the simulator's own sectors: it runs 48 readings per
lap, split Hairpin 12, Straight 6, Sweeper 14, Straight 6, Chicane 10.
"""

from functools import lru_cache
from typing import Dict, List, Tuple

from tracks.importing.geometry import LocalFrame, Point, distance, resample_closed

# The visualizer's path: five cubic Bezier curves [(start), (control 1), (control 2), (end)]
VISUALIZER_CURVES = [
    [(120, 330), (60, 250), (80, 120), (200, 100)],
    [(200, 100), (350, 80), (520, 70), (600, 140)],
    [(600, 140), (670, 200), (620, 310), (500, 330)],
    [(500, 330), (420, 340), (390, 280), (310, 280)],
    [(310, 280), (230, 280), (180, 380), (120, 330)],
]
SAMPLES_PER_CURVE = 400
LAP_LENGTH_M = 800.0
POINT_COUNT = 400
# Where the schematic is placed on the map (the same area the old placeholder corners used)
ORIGIN_LAT, ORIGIN_LNG = 12.9716, 77.5946
# The simulator's lap: readings per sector, in driving order
SIMULATOR_SECTORS: List[Tuple[str, int]] = [
    ("Hairpin", 12), ("Straight", 6), ("Sweeper", 14), ("Straight", 6), ("Chicane", 10),
]
MAX_ZONE_LENGTH_M = 100.0


def bezier_point(curve, t: float) -> Point:
    """Point at parameter t (0..1) on one cubic Bezier curve."""
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = curve
    u = 1.0 - t
    return (u**3 * x0 + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t**3 * x3,
            u**3 * y0 + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t**3 * y3)


def schematic_points_m() -> List[Point]:
    """The lap as 400 evenly spaced points in metres (x east, y north), about 800 m round."""
    dense: List[Point] = []
    for curve in VISUALIZER_CURVES:
        dense.extend(bezier_point(curve, i / SAMPLES_PER_CURVE) for i in range(SAMPLES_PER_CURVE))
    view_length = sum(distance(dense[i], dense[(i + 1) % len(dense)]) for i in range(len(dense)))
    scale = LAP_LENGTH_M / view_length
    in_metres = [(x * scale, -y * scale) for x, y in dense]
    return resample_closed(in_metres, POINT_COUNT)


@lru_cache(maxsize=1)
def schematic_outline() -> Tuple[Tuple[float, float], ...]:
    """The schematic outline as (lat, lng) pairs, computed once."""
    frame = LocalFrame(ORIGIN_LAT, ORIGIN_LNG)
    return tuple(frame.to_lat_lng(x, y) for x, y in schematic_points_m())


def schematic_outline_json() -> List[Dict[str, float]]:
    """The schematic outline as [{lat, lng}] with 7 decimals."""
    return [{"lat": round(a, 7), "lng": round(b, 7)} for a, b in schematic_outline()]


def simulator_corner_markers() -> List[Dict[str, object]]:
    """Hairpin, Sweeper and Chicane at the simulator's sector positions (centre index and length)."""
    total = sum(readings for _, readings in SIMULATOR_SECTORS)
    markers, done = [], 0
    for name, readings in SIMULATOR_SECTORS:
        if name != "Straight":
            middle_fraction = (done + readings / 2.0) / total
            sector_m = readings / total * LAP_LENGTH_M
            markers.append({
                "label": name,
                "center_index": int(round(middle_fraction * POINT_COUNT)) % POINT_COUNT,
                "length_m": min(MAX_ZONE_LENGTH_M, round(sector_m, 1)),
            })
        done += readings
    return markers
