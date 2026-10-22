"""Trackside — Shared GPS sample type and per-row checks for track imports."""

import math
from dataclasses import dataclass, field
from typing import List, Optional

# Hard limits for an upload (C2)
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_DATA_ROWS = 200_000
# A usable file needs at least this many good GPS rows
MIN_VALID_SAMPLES = 50


@dataclass
class GpsSample:
    """One good GPS row: decimal degrees and the lap number if the file has one."""

    lat: float
    lng: float
    lap: Optional[int] = None


@dataclass
class ParsedTrackFile:
    """Everything the import needs from a parsed file; nothing is saved from here."""

    source: str
    samples: List[GpsSample]
    rows_total: int
    rows_rejected: int
    session_title: str = ""
    track_name: str = ""
    notes: List[str] = field(default_factory=list)


def to_finite_float(text: str) -> Optional[float]:
    """Turn a cell into a float, or None when it is empty, not a number, NaN or infinite."""
    cleaned = (text or "").strip()
    if not cleaned or len(cleaned) > 40:
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def is_real_position(lat: Optional[float], lng: Optional[float]) -> bool:
    """True when lat/lng are numbers in range and not the (0, 0) 'no GPS fix' placeholder."""
    if lat is None or lng is None:
        return False
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
        return False
    return not (lat == 0.0 and lng == 0.0)


def to_lap_number(text: str) -> Optional[int]:
    """Read a lap cell as a whole number, or None when it is empty or odd."""
    value = to_finite_float(text)
    if value is None or value < 0 or value > 100_000:
        return None
    return int(value)
