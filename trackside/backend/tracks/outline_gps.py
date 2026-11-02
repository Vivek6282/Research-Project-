"""
Trackside — Outline points as GPS for the live track view (L1, L2).

ONE place turns an outline into latitude/longitude, used by the reference-line endpoint and the
simulator's profile export, so they cannot drift apart. Maps keep their real GPS; their profile
points use the same frame the import used.
"""

from typing import Dict, List, Sequence

from tracks.importing.geometry import LocalFrame, Point


def frame_gps_pairs(frame: LocalFrame, points_m: Sequence[Point]) -> List[List[float]]:
    """An imported map's resampled outline (local metres) as [[lat, lng]] in the frame it was made with."""
    return [[round(a, 7), round(b, 7)] for a, b in (frame.to_lat_lng(x, y) for x, y in points_m)]


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
