"""
Trackside — Pick one clean lap from a parsed session.

With a lap-number column we choose among the laps that close on themselves
(the lap whose length is closest to the typical length, which avoids in/out
laps). Without one, we find where the path first returns to its start.
"""

import statistics
from typing import List, Optional

from tracks.importing.errors import TrackImportError
from tracks.importing.geometry import LocalFrame, Point, distance, path_length
from tracks.importing.samples import GpsSample

# The path counts as closed when its two ends are this close (metres)
CLOSE_GAP_M = 25.0
# The path must first get this far from the start before a return counts
LEAVE_START_M = 60.0
# A lap shorter than this is not a kart track (metres)
MIN_LAP_LENGTH_M = 150.0
NO_LAP_MESSAGE = "Could not find one complete lap that ends where it started. Upload a session with at least one full lap."


def to_points(samples: List[GpsSample], frame: LocalFrame) -> List[Point]:
    """Convert samples to local metres."""
    return [frame.to_xy(s.lat, s.lng) for s in samples]


def is_closed(points: List[Point]) -> bool:
    """True when a path is long enough and its end is within CLOSE_GAP_M of its start."""
    return (len(points) > 10 and path_length(points) >= MIN_LAP_LENGTH_M
            and distance(points[0], points[-1]) <= CLOSE_GAP_M)


def pick_numbered_lap(samples: List[GpsSample], frame: LocalFrame) -> Optional[List[Point]]:
    """Choose the typical closed lap among the numbered laps, or None when no lap closes."""
    laps = {}
    for sample in samples:
        if sample.lap is not None:
            laps.setdefault(sample.lap, []).append(sample)
    closed = {n: to_points(rows, frame) for n, rows in laps.items()}
    closed = {n: pts for n, pts in closed.items() if is_closed(pts)}
    if not closed:
        return None
    typical = statistics.median(path_length(pts) for pts in closed.values())
    best = min(sorted(closed), key=lambda n: abs(path_length(closed[n]) - typical))
    return closed[best]


def find_first_loop(points: List[Point]) -> Optional[List[Point]]:
    """Cut the path from its first point to where it first comes back near the start."""
    left_start = False
    best_index, best_gap = None, None
    for index, point in enumerate(points):
        gap = distance(point, points[0])
        if not left_start:
            left_start = gap >= LEAVE_START_M
        elif gap <= CLOSE_GAP_M:
            if best_gap is None or gap < best_gap:
                best_index, best_gap = index, gap
        elif best_index is not None:
            break
    if best_index is None:
        return None
    loop = points[: best_index + 1]
    return loop if is_closed(loop) else None


def pick_one_lap(samples: List[GpsSample], frame: LocalFrame) -> List[Point]:
    """Return one clean lap as local-metre points, or raise TrackImportError."""
    lap = pick_numbered_lap(samples, frame) if any(s.lap is not None for s in samples) else None
    if lap is None:
        lap = find_first_loop(to_points(samples, frame))
    if lap is None:
        raise TrackImportError(NO_LAP_MESSAGE)
    return lap
