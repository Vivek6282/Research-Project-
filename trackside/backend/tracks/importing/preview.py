"""Trackside — Build the JSON the import preview screen needs (nothing is saved)."""

from tracks.importing.samples import ParsedTrackFile


def build_preview(parsed: ParsedTrackFile) -> dict:
    """Describe a parsed file for the preview response."""
    return {
        "source": parsed.source,
        "session_title": parsed.session_title,
        "track_name": parsed.track_name,
        "rows_total": parsed.rows_total,
        "rows_used": len(parsed.samples),
        "rows_rejected": parsed.rows_rejected,
    }
