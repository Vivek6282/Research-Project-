"""Trackside — Build the JSON the import preview screen needs (nothing is saved)."""

from tracks.importing.corners import DEFAULT_RADIUS_THRESHOLD_M, corner_to_json, find_corners
from tracks.importing.outline import build_outline
from tracks.importing.safe_speed import DEFAULT_LIMIT_G, LIMIT_MAX_G, LIMIT_MIN_G
from tracks.importing.samples import ParsedTrackFile


def build_preview(parsed: ParsedTrackFile, radius_threshold_m: float = DEFAULT_RADIUS_THRESHOLD_M) -> dict:
    """Describe a parsed file for the preview response."""
    outline = build_outline(parsed.samples)
    corners = find_corners(outline, radius_threshold_m)
    return {
        "source": parsed.source,
        "session_title": parsed.session_title,
        "track_name": parsed.track_name,
        "rows_total": parsed.rows_total,
        "rows_used": len(parsed.samples),
        "rows_rejected": parsed.rows_rejected,
        "outline": outline.as_lat_lng(),
        "outline_length_m": round(outline.length_m, 1),
        "outline_spacing_m": round(outline.spacing_m, 2),
        "corner_radius_m": radius_threshold_m,
        "limit_range_g": {"min": LIMIT_MIN_G, "max": LIMIT_MAX_G, "default": DEFAULT_LIMIT_G},
        "corners": [corner_to_json(i + 1, c, outline, DEFAULT_LIMIT_G) for i, c in enumerate(corners)],
    }
