"""Trackside — The checks every new or changed zone (corner) must pass, whoever sends it."""

import math
import re
from typing import Optional

MAX_LABEL_LENGTH = 40
CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
GPS_RANGE_KEYS = {"start", "end", "center", "length_m"}
MAX_GPS_LENGTH_M = 1000.0


def label_problem(value: str) -> Optional[str]:
    """Why a corner name is not allowed, or None when it is fine."""
    text = value.strip() if isinstance(value, str) else ""
    if not text:
        return "A corner name is required."
    if len(text) > MAX_LABEL_LENGTH:
        return f"A corner name can be at most {MAX_LABEL_LENGTH} characters."
    if CONTROL_CHARS.search(text):
        return "A corner name contains characters that are not allowed."
    if text.lower().startswith("straight"):
        return "A corner name cannot start with 'Straight' (that word means no corner)."
    return None


def is_coordinate(point) -> bool:
    """True for {'lat': number, 'lng': number} with both inside the earth's range."""
    if not isinstance(point, dict) or set(point) != {"lat", "lng"}:
        return False
    lat, lng = point["lat"], point["lng"]
    for value in (lat, lng):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            return False
    return -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0


def gps_range_problem(value) -> Optional[str]:
    """Why a zone's gps_range is not valid, or None. It needs start and end points; centre and length_m are optional."""
    if not isinstance(value, dict):
        return "gps_range must be an object with 'start' and 'end' points."
    if not set(value) <= GPS_RANGE_KEYS:
        return "gps_range can only hold start, end, center and length_m."
    for key in ("start", "end"):
        if not is_coordinate(value.get(key)):
            return f"gps_range.{key} must be {{'lat': -90..90, 'lng': -180..180}}."
    if "center" in value and not is_coordinate(value["center"]):
        return "gps_range.center must be {'lat': -90..90, 'lng': -180..180}."
    length = value.get("length_m")
    if "length_m" in value and (
        isinstance(length, bool) or not isinstance(length, (int, float)) or not math.isfinite(length)
        or not (0 < length <= MAX_GPS_LENGTH_M)
    ):
        return f"gps_range.length_m must be a number above 0 and at most {MAX_GPS_LENGTH_M:g}."
    return None
