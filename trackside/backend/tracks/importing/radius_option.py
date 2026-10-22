"""Trackside — Read and check the adjustable corner-radius option of an import request."""

from tracks.importing.corners import DEFAULT_RADIUS_THRESHOLD_M, MAX_RADIUS_THRESHOLD_M, MIN_RADIUS_THRESHOLD_M
from tracks.importing.errors import TrackImportError
from tracks.importing.samples import to_finite_float


def read_radius_option(raw_value) -> float:
    """Return the corner radius threshold (m) from a form value; default 60, allowed 10 to 200."""
    if raw_value in (None, ""):
        return DEFAULT_RADIUS_THRESHOLD_M
    value = to_finite_float(str(raw_value))
    if value is None or not (MIN_RADIUS_THRESHOLD_M <= value <= MAX_RADIUS_THRESHOLD_M):
        raise TrackImportError(
            f"corner_radius_m must be a number from {MIN_RADIUS_THRESHOLD_M:g} to {MAX_RADIUS_THRESHOLD_M:g}."
        )
    return value
