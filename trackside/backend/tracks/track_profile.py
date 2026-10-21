"""
Trackside — Build the track profile file the simulator reads (SIM-1).

A profile holds one closed outline in local metres (even spacing, about 2 m) and
the track's active corners: label, where they start and end on the outline, the
tightest radius inside them, and their g limit. "gps" gives the lat/lng of each outline point. It is made from the stored
Track outline and Zones only; nothing is read from the browser.
"""

import json
import os
import tempfile
from typing import List, Tuple

from tracks.importing.corners import radius_profile, sustained_radius
from tracks.importing.geometry import LocalFrame, Point, distance, path_length, resample_closed
from tracks.importing.lap_picker import CLOSE_GAP_M
from tracks.models import Track, Zone
from tracks.outline_gps import frame_gps_pairs

PROFILE_VERSION = 1
SPACING_M = 2.0
MAX_POINTS = 2000
# A corner whose start or end is farther than this from the outline cannot be placed (metres)
MAX_SNAP_DISTANCE_M = 30.0


class ProfileError(Exception):
    """The track cannot be turned into a simulator profile; the message says why."""


def load_outline(track: Track) -> Tuple[LocalFrame, List[Point], float]:
    """Resample the track's stored outline to even spacing as a closed loop of local metres."""
    line = track.reference_line
    if not isinstance(line, list) or len(line) < 50:
        raise ProfileError("This map has no outline yet (needs at least 50 points).")
    try:
        lats = [float(p["lat"]) for p in line]
        lngs = [float(p["lng"]) for p in line]
    except (KeyError, TypeError, ValueError):
        raise ProfileError("The map's outline is not a list of lat/lng points.")
    frame = LocalFrame(sum(lats) / len(lats), sum(lngs) / len(lngs))
    points = [frame.to_xy(a, b) for a, b in zip(lats, lngs)]
    if distance(points[0], points[-1]) > CLOSE_GAP_M:
        raise ProfileError("The map's outline is not a closed loop (its ends are more than 25 m apart).")
    loop_length = path_length(points + [points[0]])
    spacing = max(SPACING_M, loop_length / MAX_POINTS)
    return frame, resample_closed(points, max(int(round(loop_length / spacing)), 8)), loop_length


def nearest_index(points: List[Point], target: Point) -> Tuple[int, float]:
    """Index of the outline point closest to target, and how far away it is (metres)."""
    best = min(range(len(points)), key=lambda i: distance(points[i], target))
    return best, distance(points[best], target)


def forward_range(start: int, end: int, count: int) -> List[int]:
    """Indexes from start to end driving forward round the loop (the shorter way round)."""
    if (end - start) % count > count // 2:
        start, end = end, start
    out, i = [start], start
    while i != end and len(out) <= count:
        i = (i + 1) % count
        out.append(i)
    return out


def locate_corner(zone: Zone, frame: LocalFrame, points: List[Point], radii: List[float]):
    """Place one zone on the outline; returns its profile dict, or None when it cannot be placed."""
    box = zone.gps_range if isinstance(zone.gps_range, dict) else {}
    try:
        ends = [frame.to_xy(float(box[k]["lat"]), float(box[k]["lng"])) for k in ("start", "end")]
    except (KeyError, TypeError, ValueError):
        return None
    snapped = [nearest_index(points, p) for p in ends]
    if any(gap > MAX_SNAP_DISTANCE_M for _, gap in snapped):
        return None
    indexes = forward_range(snapped[0][0], snapped[1][0], len(points))
    tightest = min(sustained_radius(radii, i) for i in indexes)
    return {
        "label": zone.label,
        "zone_id": str(zone.id),
        "start_index": indexes[0],
        "end_index": indexes[-1],
        "tightest_radius_m": round(tightest, 2),
        "threshold_g": zone.threshold_g,
    }


def build_track_profile(track: Track) -> dict:
    """Make the profile dict for an active, non-built-in track."""
    if track.is_builtin:
        raise ProfileError("The built-in Demo Circuit uses the simulator's own track and has no profile.")
    if track.is_archived:
        raise ProfileError("This map is archived. Restore it first.")
    frame, points, loop_length = load_outline(track)
    spacing = loop_length / len(points)
    radii = radius_profile(points, spacing)
    corners, skipped = [], []
    for zone in track.zones.filter(is_active=True).order_by("label"):
        placed = locate_corner(zone, frame, points, radii)
        (corners if placed else skipped).append(placed or zone.label)
    corners.sort(key=lambda c: c["start_index"])
    return {
        "version": PROFILE_VERSION,
        "track_id": str(track.id),
        "name": track.name,
        "origin": {"lat": frame.origin_lat, "lng": frame.origin_lng},
        "spacing_m": round(spacing, 3),
        "length_m": round(loop_length, 1),
        "outline": [[round(x, 2), round(y, 2)] for x, y in points],
        "gps": frame_gps_pairs(frame, points),
        "corners": corners,
        "skipped_corners": skipped,
    }


def write_track_profile(track: Track, directory: str) -> str:
    """Write <directory>/<track uuid>.json (a fixed name, never user supplied) and return its path."""
    profile = build_track_profile(track)
    os.makedirs(directory, exist_ok=True)
    final_path = os.path.join(directory, f"{track.id}.json")
    handle, temp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        json.dump(profile, out, separators=(",", ":"))
    os.replace(temp_path, final_path)
    return final_path
