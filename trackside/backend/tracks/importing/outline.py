"""
Trackside — Build the track outline from a parsed session (C3).

Steps: choose one clean lap, resample it to even spacing (about 2 m), smooth it
lightly as a closed loop, and return it as lat/lng points. At most 2,000 points
are produced, so the same line can be drawn and saved.
"""

from dataclasses import dataclass
from typing import List

from tracks.importing.geometry import LocalFrame, Point, path_length, resample_closed, smooth_closed
from tracks.importing.lap_picker import pick_one_lap
from tracks.importing.samples import GpsSample

TARGET_SPACING_M = 2.0
MAX_OUTLINE_POINTS = 2000


@dataclass
class Outline:
    """A closed track line in local metres, plus how to map it back to lat/lng."""

    frame: LocalFrame
    points: List[Point]
    spacing_m: float

    @property
    def length_m(self) -> float:
        """Length of the closed loop in metres."""
        return path_length(self.points + [self.points[0]])

    def as_lat_lng(self) -> List[dict]:
        """The outline as [{'lat','lng'}] with 7 decimals (about 1 cm)."""
        out = []
        for x, y in self.points:
            lat, lng = self.frame.to_lat_lng(x, y)
            out.append({"lat": round(lat, 7), "lng": round(lng, 7)})
        return out


def build_outline(samples: List[GpsSample]) -> Outline:
    """Turn raw GPS samples into one smooth closed outline."""
    mean_lat = sum(s.lat for s in samples) / len(samples)
    mean_lng = sum(s.lng for s in samples) / len(samples)
    frame = LocalFrame(mean_lat, mean_lng)
    lap = pick_one_lap(samples, frame)

    # Spacing grows only for very long tracks so we never exceed MAX_OUTLINE_POINTS
    loop_length = path_length(lap + [lap[0]])
    wanted_spacing = max(TARGET_SPACING_M, loop_length / MAX_OUTLINE_POINTS)
    count = max(int(round(loop_length / wanted_spacing)), 8)
    even = resample_closed(lap, count)
    return Outline(frame=frame, points=smooth_closed(even), spacing_m=loop_length / count)
