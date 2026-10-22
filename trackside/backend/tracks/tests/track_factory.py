"""Trackside — Test helper: make a saved custom track from the synthetic rounded-rectangle lap."""

from tracks.importing.confirm import save_imported_track
from tracks.importing.corners import find_corners
from tracks.importing.outline import build_outline
from tracks.importing.racechrono_csv import parse_racechrono_csv
from tracks.tests import synthetic_track as st


def make_imported_track(user, name="Factory Track", limit=1.2):
    """Save the synthetic track through the real import code; returns the Track (4 corners, sprint class)."""
    parsed = parse_racechrono_csv(st.racechrono_csv_text(st.make_samples(laps=3)))
    outline = build_outline(parsed.samples)
    corners = find_corners(outline)
    choices = [{"label": f"Corner {n}", "threshold_g": limit} for n in range(1, len(corners) + 1)]
    return save_imported_track(user, name, parsed, outline, corners, choices)
