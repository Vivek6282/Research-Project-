"""
Trackside Virtual Lap Simulator — GPS points for each reading.
The backend writes the same point list the Live Track View draws; the simulator
only reads it (a --gps-file for the built-in track, the profile's "gps" list for
imported maps) and gives each reading one point from it.
"""

import json
import math
import os
from typing import List, Optional, Tuple

MAX_GPS_FILE_BYTES = 5 * 1024 * 1024
MAX_GPS_POINTS = 5000

GpsPoint = Tuple[float, float]


class GpsLoadError(Exception):
    """The GPS file is missing, too big, not JSON, or has bad values; the message says what."""


def parse_gps_points(raw_points) -> List[GpsPoint]:
    """Check a list of [lat, lng] pairs and return it as tuples."""
    if not isinstance(raw_points, list) or not (2 <= len(raw_points) <= MAX_GPS_POINTS):
        raise GpsLoadError(f"GPS points must be a list of 2 to {MAX_GPS_POINTS} pairs.")
    points = []
    for item in raw_points:
        ok = isinstance(item, (list, tuple)) and len(item) == 2 and all(
            isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in item)
        if not ok or not (-90 <= item[0] <= 90 and -180 <= item[1] <= 180):
            raise GpsLoadError("Every GPS point must be [lat, lng] with real coordinates.")
        points.append((float(item[0]), float(item[1])))
    return points


def load_gps_file(path: str) -> List[GpsPoint]:
    """Load <track id>.gps.json ({"version": 1, "points": [[lat, lng], ...]}); raises GpsLoadError on any problem."""
    if not os.path.isfile(path):
        raise GpsLoadError(f"GPS file not found: {path}")
    if os.path.getsize(path) > MAX_GPS_FILE_BYTES:
        raise GpsLoadError("GPS file is larger than 5 MB.")
    try:
        with open(path, encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, ValueError) as error:
        raise GpsLoadError(f"GPS file is not valid JSON: {error}")
    if not isinstance(raw, dict) or raw.get("version") != 1:
        raise GpsLoadError("Unsupported GPS file (expected version 1).")
    return parse_gps_points(raw.get("points"))


def gps_for_reading(points: Optional[List[GpsPoint]], reading_number: int, readings_per_lap: int) -> Optional[GpsPoint]:
    """The point for reading k of a lap: the lap's readings are spread evenly round the whole outline."""
    if not points or readings_per_lap <= 0:
        return None
    return points[(reading_number % readings_per_lap) * len(points) // readings_per_lap]


def load_gps_or_exit(path: Optional[str]) -> Optional[List[GpsPoint]]:
    """For the command line: None when no file was given; otherwise the points, or print the problem and exit 2."""
    if not path:
        return None
    try:
        return load_gps_file(path)
    except GpsLoadError as error:
        print(f"Error: {error}")
        raise SystemExit(2)
