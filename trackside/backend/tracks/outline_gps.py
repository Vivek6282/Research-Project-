"""
Trackside — Outline points as GPS for the live track view (L1, L2).

ONE place turns an outline into latitude/longitude, used by the reference-line endpoint,
the simulator's profile export and the built-in map's GPS file, so they cannot drift apart.

The built-in Demo Circuit has no survey, so its drawn (schematic) outline in metres is placed
on PSEUDO coordinates around a fixed origin (lat 10.0, lng 76.0). Nothing is stored on the track.
Imported maps keep their real GPS; their profile points use the same frame the import used.
"""

import json
import math
import os
import tempfile
from functools import lru_cache
from typing import Dict, List, Sequence, Tuple

from tracks.demo_circuit import MAX_ZONE_LENGTH_M, schematic_points_m, simulator_corner_markers
from tracks.importing.geometry import LocalFrame, Point

PSEUDO_ORIGIN_LAT, PSEUDO_ORIGIN_LNG = 10.0, 76.0
METERS_PER_DEGREE_LAT = 111_320.0
SCHEMATIC_SPACING_M = 2.0
Pair = Tuple[float, float]


def pseudo_gps(x_m: float, y_m: float) -> Pair:
    """Metres (x east, y north) from the pseudo origin to (lat, lng); longitude is scaled by cos(latitude)."""
    lat = PSEUDO_ORIGIN_LAT + y_m / METERS_PER_DEGREE_LAT
    lng = PSEUDO_ORIGIN_LNG + x_m / (METERS_PER_DEGREE_LAT * math.cos(math.radians(PSEUDO_ORIGIN_LAT)))
    return round(lat, 7), round(lng, 7)


@lru_cache(maxsize=1)
def schematic_gps_pairs() -> Tuple[Pair, ...]:
    """The built-in map's schematic outline as pseudo (lat, lng) pairs, 400 points, computed once."""
    return tuple(pseudo_gps(x, y) for x, y in schematic_points_m())


def schematic_reference_line() -> List[Dict[str, float]]:
    """The same points as [{lat, lng}], the shape /reference-line/ returns."""
    return [{"lat": lat, "lng": lng} for lat, lng in schematic_gps_pairs()]


def frame_gps_pairs(frame: LocalFrame, points_m: Sequence[Point]) -> List[List[float]]:
    """An imported map's resampled outline (local metres) as [[lat, lng]] in the frame it was made with."""
    return [[round(a, 7), round(b, 7)] for a, b in (frame.to_lat_lng(x, y) for x, y in points_m)]


def schematic_corner_segments(zones) -> List[Dict[str, object]]:
    """Hairpin, Sweeper and Chicane as outline segments (start, end, centre) at the simulator's sector positions."""
    pairs = schematic_gps_pairs()
    count = len(pairs)
    by_label = {z.label.lower(): z for z in zones}
    corners = []
    for marker in simulator_corner_markers():
        zone = by_label.get(str(marker["label"]).lower())
        if zone is None:
            continue
        half = max(1, int(round(min(float(marker["length_m"]), MAX_ZONE_LENGTH_M) / 2.0 / SCHEMATIC_SPACING_M)))
        centre = int(marker["center_index"])
        corners.append({
            "zone_id": str(zone.id), "label": zone.label,
            "start": dict(zip(("lat", "lng"), pairs[(centre - half) % count])),
            "end": dict(zip(("lat", "lng"), pairs[(centre + half) % count])),
            "center": dict(zip(("lat", "lng"), pairs[centre])),
        })
    return corners


def stored_corner_segments(zones) -> List[Dict[str, object]]:
    """A custom map's corners exactly as stored in each zone's gps_range (nothing invented)."""
    corners = []
    for zone in zones:
        box = zone.gps_range if isinstance(zone.gps_range, dict) else {}
        if "start" in box and "end" in box:
            corner = {"zone_id": str(zone.id), "label": zone.label, "start": box["start"], "end": box["end"]}
            if "center" in box:
                corner["center"] = box["center"]
            corners.append(corner)
    return corners


def write_schematic_gps_file(directory: str, track_id) -> str:
    """Write <directory>/<track id>.gps.json ({version, points}) for the simulator's built-in run; returns the path."""
    os.makedirs(directory, exist_ok=True)
    final_path = os.path.join(directory, f"{track_id}.gps.json")
    handle, temp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        json.dump({"version": 1, "points": [list(p) for p in schematic_gps_pairs()]}, out, separators=(",", ":"))
    os.replace(temp_path, final_path)
    return final_path
