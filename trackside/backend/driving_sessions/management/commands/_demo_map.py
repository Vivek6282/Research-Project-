"""Trackside — shared by the seed commands: find the map to seed on and its three simulator corners."""

from django.core.management.base import CommandError

from tracks.models import Track

SIMULATOR_CORNERS = ("Hairpin", "Sweeper", "Chicane")


def add_track_argument(parser):
    """Add the required --track-name option."""
    parser.add_argument("--track-name", required=True, help="Name of an existing map that has corners called Hairpin, Sweeper and Chicane")


def find_map(name):
    """The active map with this name and its Hairpin, Sweeper and Chicane corners, or a clear CommandError."""
    track = Track.objects.filter(name__iexact=name, is_archived=False).first()
    if track is None:
        raise CommandError(f"No active map called '{name}'. Add it on the Maps screen first.")
    zones = {z.label: z for z in track.zones.filter(is_active=True) if z.label in SIMULATOR_CORNERS}
    missing = [c for c in SIMULATOR_CORNERS if c not in zones]
    if missing:
        raise CommandError(f"Map '{track.name}' has no corner called {', '.join(missing)}. The simulator needs all of {', '.join(SIMULATOR_CORNERS)}.")
    return track, zones
