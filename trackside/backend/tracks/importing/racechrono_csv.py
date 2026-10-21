"""
Trackside — RaceChrono CSV v3 reader.

Layout (RaceChrono 7.3+): a 'Key,Value' preamble, then a header row of channel
names, then a units row and a source row, then data. The same channel (for
example latitude) can appear twice from different sources; we prefer the GPS one.
Only the standard csv module is used.
"""

import csv
import io
from typing import Dict, List, Optional

from tracks.importing.errors import TrackImportError
from tracks.importing.samples import (
    MAX_DATA_ROWS, GpsSample, ParsedTrackFile, is_real_position, to_finite_float, to_lap_number,
)

LAT_NAMES = {"latitude", "lat"}
LNG_NAMES = {"longitude", "lon", "lng", "long"}
LAP_NAMES = {"lap", "lap_number", "lap_no", "lap_num", "lap_nr"}
# How far down the file we look for the header row
MAX_PREAMBLE_ROWS = 200


def normalize_name(cell: str) -> str:
    """Lower-case a channel name and turn spaces/dashes into underscores."""
    return cell.strip().lower().replace(" ", "_").replace("-", "_")


def find_header_index(rows: List[List[str]]) -> int:
    """Return the index of the row that names the channels, or raise if there is none."""
    for index, row in enumerate(rows[:MAX_PREAMBLE_ROWS]):
        names = {normalize_name(cell) for cell in row}
        if names & LAT_NAMES and names & LNG_NAMES:
            return index
    raise TrackImportError("No latitude/longitude header row found. Is this a RaceChrono CSV v3 export?")


def columns_named(header: List[str], wanted: set) -> List[int]:
    """List every column index whose normalized name is in the wanted set."""
    return [i for i, cell in enumerate(header) if normalize_name(cell) in wanted]


def is_descriptor_row(row: List[str], lat_col: int, lng_col: int) -> bool:
    """True for a units/source row: the latitude and longitude cells are not numbers."""
    lat_cell = row[lat_col] if lat_col < len(row) else ""
    lng_cell = row[lng_col] if lng_col < len(row) else ""
    return to_finite_float(lat_cell) is None and to_finite_float(lng_cell) is None


def pick_position_columns(header: List[str], descriptors: List[List[str]]) -> Dict[str, Optional[int]]:
    """Choose the latitude/longitude/lap columns, preferring channels whose source says 'gps'."""
    lat_options = columns_named(header, LAT_NAMES)
    lng_options = columns_named(header, LNG_NAMES)
    lap_options = columns_named(header, LAP_NAMES)

    def says_gps(col: int) -> bool:
        """True when a units/source row marks this column as GPS."""
        return any(col < len(row) and "gps" in row[col].lower() for row in descriptors)

    lat_col = next((c for c in lat_options if says_gps(c)), lat_options[0])
    lng_col = next((c for c in lng_options if says_gps(c)), lng_options[0])
    return {"lat": lat_col, "lng": lng_col, "lap": lap_options[0] if lap_options else None}


def read_preamble(rows: List[List[str]], header_index: int) -> Dict[str, str]:
    """Collect the 'Key,Value' lines above the header, keyed in lower case."""
    meta = {}
    for row in rows[:header_index]:
        if len(row) >= 2 and row[0].strip():
            meta[row[0].strip().lower()] = row[1].strip()[:150]
    return meta


def parse_racechrono_csv(text: str) -> ParsedTrackFile:
    """Parse CSV v3 text into good GPS samples; bad rows are counted and dropped."""
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except csv.Error as error:
        raise TrackImportError(f"The CSV file could not be read: {error}")

    header_index = find_header_index(rows)
    header = rows[header_index]
    body = rows[header_index + 1:]

    # Up to two descriptor rows (units, source) sit right under the header
    descriptors: List[List[str]] = []
    probe = columns_named(header, LAT_NAMES)[0], columns_named(header, LNG_NAMES)[0]
    while body and len(descriptors) < 2 and is_descriptor_row(body[0], *probe):
        descriptors.append(body.pop(0))

    cols = pick_position_columns(header, descriptors)
    samples, rows_total, rows_rejected = [], 0, 0
    for row in body:
        if not any(cell.strip() for cell in row):
            continue
        rows_total += 1
        if rows_total > MAX_DATA_ROWS:
            raise TrackImportError(f"Too many data rows (limit is {MAX_DATA_ROWS:,}).")
        lat = to_finite_float(row[cols["lat"]]) if cols["lat"] < len(row) else None
        lng = to_finite_float(row[cols["lng"]]) if cols["lng"] < len(row) else None
        if not is_real_position(lat, lng):
            rows_rejected += 1
            continue
        lap = None
        if cols["lap"] is not None and cols["lap"] < len(row):
            lap = to_lap_number(row[cols["lap"]])
        samples.append(GpsSample(lat=lat, lng=lng, lap=lap))

    meta = read_preamble(rows, header_index)
    return ParsedTrackFile(
        source="racechrono_csv",
        samples=samples,
        rows_total=rows_total,
        rows_rejected=rows_rejected,
        session_title=meta.get("session title", ""),
        track_name=meta.get("track name", ""),
    )
