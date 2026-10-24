"""
Trackside — Place phone readings on the track: which corner, which lap (Phase 2.1).

A phone only knows where it is (GPS). The server, not the phone, decides which
corner each reading is in and which lap it belongs to, so a phone cannot claim
a different corner or lap. It reuses the simulator's track profile: the track
outline at about 2 m spacing, with each active corner as a range of outline
points. A lap is counted when the kart passes the outline's first point (the
start/finish line of a drawn or imported map).
"""

import hashlib
import json
from typing import Dict, List, Optional, Tuple

from django.core.cache import cache

from driving_sessions.models import Telemetry
from tracks.importing.geometry import LocalFrame
from tracks.models import Zone
from tracks.track_profile import ProfileError, build_track_profile

PROFILE_CACHE_SECONDS = 600
# Farther than this from the outline counts as off the track (pit lane, paddock): no corner
OFF_TRACK_M = 30.0
# Nearby-first search: look this many outline points around the last position before scanning all
NEARBY_POINTS = 60
NEARBY_ACCEPT_M = 15.0
# A lap is counted when the position jumps from the last fifth of the outline to the first fifth
LAP_WRAP_FRACTION = 0.2


def track_fingerprint(track) -> str:
    """A short hash that changes whenever the outline or any active corner of the track changes."""
    zones = list(track.zones.filter(is_active=True).order_by("id").values_list("id", "gps_range", "threshold_g"))
    text = json.dumps([track.reference_line, [[str(z), r, g] for z, r, g in zones]], sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


def placement_profile(track) -> dict:
    """The outline (local metres), its origin and the corners as outline ranges; cached per track version."""
    key = f"phone-profile:{track.id}:{track_fingerprint(track)}"
    profile = cache.get(key)
    if profile is None:
        full = build_track_profile(track)
        profile = {"origin": full["origin"], "outline": full["outline"],
                   "corners": [{"zone_id": c["zone_id"], "start": c["start_index"], "end": c["end_index"]}
                               for c in full["corners"]]}
        cache.set(key, profile, PROFILE_CACHE_SECONDS)
    return profile


def track_supports_phone(track) -> Optional[str]:
    """None when phone readings can be placed on this track, otherwise the reason they cannot."""
    try:
        placement_profile(track)
    except ProfileError as error:
        return str(error)
    return None


class Placer:
    """Walks through readings in time order, keeping the last position and lap between them."""

    def __init__(self, profile: dict, last_index: Optional[int] = None, lap: int = 1):
        """Start from the session's last placed reading (or the first lap)."""
        self.frame = LocalFrame(profile["origin"]["lat"], profile["origin"]["lng"])
        self.outline: List[Tuple[float, float]] = [tuple(p) for p in profile["outline"]]
        self.corners = profile["corners"]
        self.last_index, self.lap = last_index, lap

    def nearest(self, x: float, y: float) -> Tuple[int, float]:
        """Closest outline point to (x, y) and its distance; tries near the last position first."""
        count = len(self.outline)
        candidates = range(count)
        if self.last_index is not None:
            nearby = [(self.last_index + step) % count for step in range(-NEARBY_POINTS, NEARBY_POINTS + 1)]
            best = min(nearby, key=lambda i: (self.outline[i][0] - x) ** 2 + (self.outline[i][1] - y) ** 2)
            gap = ((self.outline[best][0] - x) ** 2 + (self.outline[best][1] - y) ** 2) ** 0.5
            if gap <= NEARBY_ACCEPT_M:
                return best, gap
        best = min(candidates, key=lambda i: (self.outline[i][0] - x) ** 2 + (self.outline[i][1] - y) ** 2)
        return best, ((self.outline[best][0] - x) ** 2 + (self.outline[best][1] - y) ** 2) ** 0.5

    def corner_at(self, index: int) -> Optional[str]:
        """The zone id whose outline range holds this point, or None on a straight."""
        for corner in self.corners:
            start, end = corner["start"], corner["end"]
            inside = start <= index <= end if start <= end else (index >= start or index <= end)
            if inside:
                return corner["zone_id"]
        return None

    def place(self, lat: float, lng: float) -> Tuple[Optional[str], int]:
        """(zone id or None, lap number) for one position; off the track keeps the lap and has no corner."""
        index, gap = self.nearest(*self.frame.to_xy(lat, lng))
        if gap > OFF_TRACK_M:
            return None, self.lap
        count = len(self.outline)
        if (self.last_index is not None and self.last_index > count * (1 - LAP_WRAP_FRACTION)
                and index < count * LAP_WRAP_FRACTION):
            self.lap += 1
        self.last_index = index
        return self.corner_at(index), self.lap


def placer_for_session(session, profile: dict) -> Placer:
    """A Placer that continues from the session's latest stored reading."""
    last = (Telemetry.objects.filter(session=session).order_by("-recorded_at")
            .values("gps_lat", "gps_lng", "lap_number").first())
    placer = Placer(profile)
    if last and last["gps_lat"] is not None and last["gps_lng"] is not None:
        index, gap = placer.nearest(*placer.frame.to_xy(last["gps_lat"], last["gps_lng"]))
        placer.last_index = index if gap <= OFF_TRACK_M else None
        placer.lap = last["lap_number"] or 1
    return placer


def assign_positions(session, readings: List[Dict]) -> None:
    """Set "zone" and "lap_number" on each validated reading (sorted by time) from its GPS position."""
    placer = placer_for_session(session, placement_profile(session.track))
    zones = {str(z.id): z for z in Zone.objects.filter(track=session.track, is_active=True)}
    for reading in readings:
        zone_id, lap = placer.place(reading["gps_lat"], reading["gps_lng"])
        reading["zone"] = zones.get(zone_id) if zone_id else None
        reading["lap_number"] = lap
