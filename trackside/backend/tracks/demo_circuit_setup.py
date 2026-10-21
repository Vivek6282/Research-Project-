"""Trackside — Make sure the built-in Demo Circuit and its three corners exist (idempotent)."""

import threading

from django.db import transaction

from tracks.models import Track, Zone

# Two requests at once (for example the browser asking twice) must not both create the Demo Circuit
_ENSURE_LOCK = threading.Lock()

DEMO_CIRCUIT_NAME = "Demo Circuit"
# The simulator's three corners and their default limits (the Sweeper's 1.55 g is the demo's own value)
DEMO_CORNERS = [
    ("Hairpin", 1.15, Zone.CornerType.HAIRPIN),
    ("Sweeper", 1.55, Zone.CornerType.SWEEPER),
    ("Chicane", 1.30, Zone.CornerType.CHICANE),
]
# Placeholder positions: the Demo Circuit has no GPS survey (its schematic outline is in demo_circuit.py)
PLACEHOLDER_GPS = {
    "start": {"lat": 12.9716, "lng": 77.5946},
    "end": {"lat": 12.9720, "lng": 77.5950},
}


def ensure_demo_circuit() -> Track:
    """Return the built-in Demo Circuit, creating it and any missing corner without changing existing ones."""
    with _ENSURE_LOCK, transaction.atomic():
        return _ensure_demo_circuit_locked()


def _ensure_demo_circuit_locked() -> Track:
    """The work of ensure_demo_circuit, run while holding the lock."""
    track = Track.objects.filter(name=DEMO_CIRCUIT_NAME).order_by("-is_builtin").first()
    if track is None:
        track = Track.objects.create(
            name=DEMO_CIRCUIT_NAME, kart_class=Track.KartClass.SPRINT, is_builtin=True, source=Track.Source.BUILTIN,
        )
    if not track.is_builtin or track.source != Track.Source.BUILTIN or track.kart_class != Track.KartClass.SPRINT:
        track.is_builtin, track.source, track.kart_class = True, Track.Source.BUILTIN, Track.KartClass.SPRINT
        track.save(update_fields=["is_builtin", "source", "kart_class"])
    for label, limit, corner_type in DEMO_CORNERS:
        Zone.objects.get_or_create(
            track=track, label=label,
            defaults={"threshold_g": limit, "corner_type": corner_type, "gps_range": PLACEHOLDER_GPS},
        )
    return track
