"""
Trackside — Racelogic VBO reader.

A VBO file is text with sections: [header], [column names] and [data]; data rows
are space separated. Latitude and longitude are NOT decimal degrees: Racelogic
writes them in minutes (degrees x 60), latitude positive = North and longitude
positive = WEST. We convert to decimal degrees with East positive.
NOTE: this sign/unit rule comes from Racelogic's VBOX documentation and is
checked here only against a synthetic file, not against a real recording.
"""

from typing import Dict, List

from tracks.importing.errors import TrackImportError
from tracks.importing.samples import (
    MAX_DATA_ROWS, GpsSample, ParsedTrackFile, is_real_position, to_finite_float, to_lap_number,
)

LAT_NAMES = {"lat", "latitude"}
LNG_NAMES = {"long", "lon", "longitude"}
LAP_NAMES = {"lap", "lapnumber", "lap_number"}
# Largest valid values in minutes: 90 x 60 and 180 x 60
MAX_LAT_MINUTES = 5400.0
MAX_LNG_MINUTES = 10800.0


def split_sections(text: str) -> Dict[str, List[str]]:
    """Group the file's non-empty lines under their [section] name (lower case)."""
    sections: Dict[str, List[str]] = {}
    current = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip().lower()
            sections.setdefault(current, [])
        elif current:
            sections[current].append(line)
    return sections


def find_column(names: List[str], wanted: set) -> int:
    """Return the first column whose lower-case name is wanted, or -1."""
    for index, name in enumerate(names):
        if name.lower() in wanted:
            return index
    return -1


def minutes_to_position(lat_minutes: float, lng_minutes: float):
    """Convert VBO minutes (longitude positive = West) to decimal degrees (East positive)."""
    if abs(lat_minutes) > MAX_LAT_MINUTES or abs(lng_minutes) > MAX_LNG_MINUTES:
        return None, None
    return lat_minutes / 60.0, -lng_minutes / 60.0


def parse_vbo(text: str) -> ParsedTrackFile:
    """Parse VBO text into good GPS samples; bad rows are counted and dropped."""
    sections = split_sections(text)
    if "column names" not in sections or "data" not in sections or not sections["column names"]:
        raise TrackImportError("Not a VBO file: the [column names] or [data] section is missing.")

    names = sections["column names"][0].split()
    lat_col = find_column(names, LAT_NAMES)
    lng_col = find_column(names, LNG_NAMES)
    lap_col = find_column(names, LAP_NAMES)
    if lat_col < 0 or lng_col < 0:
        raise TrackImportError("The VBO file has no latitude/longitude columns.")

    samples, rows_total, rows_rejected = [], 0, 0
    for line in sections["data"]:
        rows_total += 1
        if rows_total > MAX_DATA_ROWS:
            raise TrackImportError(f"Too many data rows (limit is {MAX_DATA_ROWS:,}).")
        cells = line.split()
        lat_min = to_finite_float(cells[lat_col]) if lat_col < len(cells) else None
        lng_min = to_finite_float(cells[lng_col]) if lng_col < len(cells) else None
        lat, lng = (None, None)
        if lat_min is not None and lng_min is not None:
            lat, lng = minutes_to_position(lat_min, lng_min)
        if not is_real_position(lat, lng):
            rows_rejected += 1
            continue
        lap = to_lap_number(cells[lap_col]) if 0 <= lap_col < len(cells) else None
        samples.append(GpsSample(lat=lat, lng=lng, lap=lap))

    return ParsedTrackFile(
        source="vbo", samples=samples, rows_total=rows_total, rows_rejected=rows_rejected,
    )
