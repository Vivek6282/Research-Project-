"""
Trackside — Safe handling of an uploaded track file.

Checks the name, size and text encoding, hands the text to the right reader,
and refuses files with too few good GPS rows. Nothing here saves anything.
"""

import os

from tracks.importing.errors import TrackImportError
from tracks.importing.racechrono_csv import parse_racechrono_csv
from tracks.importing.samples import MAX_FILE_BYTES, MIN_VALID_SAMPLES, ParsedTrackFile
from tracks.importing.vbo import parse_vbo

ALLOWED_EXTENSIONS = {".csv": parse_racechrono_csv, ".vbo": parse_vbo}


def read_upload_text(uploaded_file) -> str:
    """Return the file's text after size, null-byte and UTF-8 checks."""
    if uploaded_file.size > MAX_FILE_BYTES:
        raise TrackImportError("The file is larger than 5 MB.", status_code=413)
    raw = uploaded_file.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise TrackImportError("The file is larger than 5 MB.", status_code=413)
    if b"\x00" in raw:
        raise TrackImportError("This looks like a binary file, not a CSV or VBO text file.")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise TrackImportError("The file is not valid UTF-8 text.")


def parse_uploaded_track_file(uploaded_file) -> ParsedTrackFile:
    """Check an upload and parse it into GPS samples, or raise TrackImportError."""
    if uploaded_file is None:
        raise TrackImportError("Attach a .csv or .vbo file in the 'file' field.")
    extension = os.path.splitext(uploaded_file.name or "")[1].lower()
    reader = ALLOWED_EXTENSIONS.get(extension)
    if reader is None:
        raise TrackImportError("Only .csv (RaceChrono) and .vbo (Racelogic) files are accepted.")
    parsed = reader(read_upload_text(uploaded_file))
    if len(parsed.samples) < MIN_VALID_SAMPLES:
        raise TrackImportError(
            f"Only {len(parsed.samples)} usable GPS rows found; at least {MIN_VALID_SAMPLES} are needed."
        )
    return parsed
