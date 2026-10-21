"""
Trackside Virtual Lap Simulator — Track Profile Loader.
Reads and strictly checks the JSON profile written by `manage.py export_track`
(one closed outline in metres plus the track's corners) for --track-file runs.
"""

import json
import math
import os
from dataclasses import dataclass, field
from typing import List, Tuple

MAX_PROFILE_BYTES = 5 * 1024 * 1024
MIN_OUTLINE_POINTS = 20
MAX_OUTLINE_POINTS = 5000
MAX_LABEL_LENGTH = 40


class ProfileLoadError(Exception):
    """The profile file is missing, too big, not JSON, or has bad values; the message says what."""


@dataclass
class ProfileCorner:
    """One corner: where it sits on the outline, its tightest radius and its g limit."""

    label: str
    start_index: int
    end_index: int
    tightest_radius_m: float
    threshold_g: float
    zone_id: str = ""


@dataclass
class TrackProfile:
    """A closed outline in local metres and its corners, as loaded from a profile file."""

    name: str
    track_id: str
    spacing_m: float
    length_m: float
    outline: List[Tuple[float, float]]
    corners: List[ProfileCorner] = field(default_factory=list)


def finite_number(value, name: str, low: float, high: float) -> float:
    """Return value as a float inside [low, high], or raise ProfileLoadError naming the field."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ProfileLoadError(f"'{name}' must be a number.")
    if not (low <= value <= high):
        raise ProfileLoadError(f"'{name}' must be between {low} and {high}.")
    return float(value)


def parse_outline(raw_outline) -> List[Tuple[float, float]]:
    """Check the outline is a list of [x, y] metre pairs of a sensible size."""
    if not isinstance(raw_outline, list) or not (MIN_OUTLINE_POINTS <= len(raw_outline) <= MAX_OUTLINE_POINTS):
        raise ProfileLoadError(f"'outline' must be a list of {MIN_OUTLINE_POINTS} to {MAX_OUTLINE_POINTS} points.")
    points = []
    for item in raw_outline:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ProfileLoadError("Every outline point must be [x, y].")
        points.append((finite_number(item[0], "outline x", -1e5, 1e5), finite_number(item[1], "outline y", -1e5, 1e5)))
    return points


def parse_corner(raw_corner, point_count: int) -> ProfileCorner:
    """Check one corner entry against the outline size."""
    if not isinstance(raw_corner, dict):
        raise ProfileLoadError("Every corner must be an object.")
    label = raw_corner.get("label")
    if not isinstance(label, str) or not (1 <= len(label.strip()) <= MAX_LABEL_LENGTH) or label.strip().lower().startswith("straight"):
        raise ProfileLoadError("Every corner needs a name of 1 to 40 characters that does not start with 'Straight'.")
    indexes = []
    for key in ("start_index", "end_index"):
        value = raw_corner.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or not (0 <= value < point_count):
            raise ProfileLoadError(f"Corner '{label}': '{key}' must be a whole number inside the outline.")
        indexes.append(value)
    return ProfileCorner(
        label=label.strip(),
        start_index=indexes[0],
        end_index=indexes[1],
        tightest_radius_m=finite_number(raw_corner.get("tightest_radius_m"), f"{label} tightest_radius_m", 1.0, 5000.0),
        threshold_g=finite_number(raw_corner.get("threshold_g"), f"{label} threshold_g", 0.1, 5.0),
        zone_id=str(raw_corner.get("zone_id", ""))[:64],
    )


def load_profile(path: str) -> TrackProfile:
    """Load and fully check a profile file; raises ProfileLoadError with a clear message on any problem."""
    if not os.path.isfile(path):
        raise ProfileLoadError(f"Track file not found: {path}")
    if os.path.getsize(path) > MAX_PROFILE_BYTES:
        raise ProfileLoadError("Track file is larger than 5 MB.")
    try:
        with open(path, encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, ValueError) as error:
        raise ProfileLoadError(f"Track file is not valid JSON: {error}")
    if not isinstance(raw, dict) or raw.get("version") != 1:
        raise ProfileLoadError("Unsupported track file (expected version 1).")
    outline = parse_outline(raw.get("outline"))
    raw_corners = raw.get("corners")
    if not isinstance(raw_corners, list) or len(raw_corners) > 200:
        raise ProfileLoadError("'corners' must be a list of up to 200 corners.")
    corners = [parse_corner(c, len(outline)) for c in raw_corners]
    labels = [c.label.lower() for c in corners]
    if len(set(labels)) != len(labels):
        raise ProfileLoadError("Corner names must be different from each other.")
    return TrackProfile(
        name=str(raw.get("name", ""))[:150],
        track_id=str(raw.get("track_id", ""))[:64],
        spacing_m=finite_number(raw.get("spacing_m"), "spacing_m", 0.5, 20.0),
        length_m=finite_number(raw.get("length_m"), "length_m", 50.0, 100000.0),
        outline=outline,
        corners=corners,
    )
