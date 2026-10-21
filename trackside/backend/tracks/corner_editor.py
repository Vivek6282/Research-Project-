"""
Trackside — Corner marker editor logic (H3).

A marker is a point on the track outline (an index into the editor outline), a
name, a g limit and a zone length. Saving turns markers into Zones: label,
threshold_g and a gps_range for the zone segment centred on the marker. Markers
whose zone already has history are deactivated instead of deleted.
"""

import hashlib
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from django.db import transaction

from tracks.demo_circuit import ORIGIN_LAT, ORIGIN_LNG, schematic_points_m, simulator_corner_markers
from tracks.importing.corners import find_corners, radius_profile, sustained_radius
from tracks.importing.geometry import LocalFrame, Point, distance
from tracks.importing.outline import Outline
from tracks.limit_history import set_zone_limit
from tracks.models import Track, Zone
from tracks.track_profile import MAX_SNAP_DISTANCE_M, ProfileError, forward_range, load_outline
from tracks.zone_retirement import DEACTIVATED, DELETED, retire_zone

ZONE_LENGTH_MIN_M, ZONE_LENGTH_MAX_M, ZONE_LENGTH_DEFAULT_M = 10.0, 100.0, 30.0
MAX_MARKERS = 60
MAX_LABEL_LENGTH = 40
CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
NO_CURVE_RADIUS_M = 9999.0


class CornerEditError(Exception):
    """A problem the coach can fix (or a locked map); the message is shown to them."""

    def __init__(self, message: str, status_code: int = 400):
        """Keep the user-facing message and the HTTP status to answer with."""
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass
class EditorOutline:
    """The closed outline a marker index refers to, with its radius at every point."""

    frame: LocalFrame
    points: List[Point]
    spacing_m: float
    radii: List[float]
    is_schematic: bool

    @property
    def count(self) -> int:
        """Number of outline points."""
        return len(self.points)

    @property
    def version(self) -> str:
        """Short fingerprint of the outline; a save made against an older outline is refused."""
        text = f"{self.count}|{self.points[0]}|{self.points[self.count // 2]}|{self.points[-1]}"
        return hashlib.sha1(text.encode()).hexdigest()[:12]

    def lat_lng(self, index: int) -> Dict[str, float]:
        """Lat/lng of one outline point."""
        lat, lng = self.frame.to_lat_lng(*self.points[index % self.count])
        return {"lat": round(lat, 7), "lng": round(lng, 7)}


def editor_outline(track: Track) -> EditorOutline:
    """Build the editor outline: the schematic for the built-in map, otherwise the stored outline."""
    if track.is_builtin:
        points = schematic_points_m()
        frame, spacing, schematic = LocalFrame(ORIGIN_LAT, ORIGIN_LNG), 2.0, True
    else:
        try:
            frame, points, loop_length = load_outline(track)
        except ProfileError as error:
            raise CornerEditError(str(error), 409)
        spacing, schematic = loop_length / len(points), False
    radii = radius_profile(points, spacing)
    sustained = [min(sustained_radius(radii, i), NO_CURVE_RADIUS_M) for i in range(len(points))]
    return EditorOutline(frame=frame, points=points, spacing_m=spacing, radii=sustained, is_schematic=schematic)


def segment_indexes(center: int, length_m: float, editor: EditorOutline) -> List[int]:
    """Outline indexes of a zone segment of the given length centred on a point."""
    half = max(1, int(round(length_m / 2.0 / editor.spacing_m)))
    count = editor.count
    return [(center + k) % count for k in range(-half, half + 1)]


def marker_radius(center: int, length_m: float, editor: EditorOutline) -> float:
    """Tightest radius (m) inside the marker's zone segment."""
    return min(editor.radii[i] for i in segment_indexes(center, length_m, editor))


def snap_to_outline(editor: EditorOutline, lat: float, lng: float) -> Optional[int]:
    """Index of the outline point nearest a lat/lng, or None when it is more than 30 m away."""
    target = editor.frame.to_xy(lat, lng)
    best = min(range(editor.count), key=lambda i: distance(editor.points[i], target))
    return best if distance(editor.points[best], target) <= MAX_SNAP_DISTANCE_M else None


def zone_position(zone: Zone, editor: EditorOutline):
    """Work out (center_index, length_m) of a stored zone, or (None, default length) if it cannot be placed."""
    box = zone.gps_range if isinstance(zone.gps_range, dict) else {}
    try:
        if editor.is_schematic:
            known = {m["label"].lower(): m for m in simulator_corner_markers()}
            marker = known.get(zone.label.lower())
            return (marker["center_index"], marker["length_m"]) if marker else (None, ZONE_LENGTH_DEFAULT_M)
        start = snap_to_outline(editor, float(box["start"]["lat"]), float(box["start"]["lng"]))
        end = snap_to_outline(editor, float(box["end"]["lat"]), float(box["end"]["lng"]))
    except (KeyError, TypeError, ValueError):
        return None, ZONE_LENGTH_DEFAULT_M
    if start is None or end is None:
        return None, ZONE_LENGTH_DEFAULT_M
    indexes = forward_range(start, end, editor.count)
    length = min(max((len(indexes) - 1) * editor.spacing_m, ZONE_LENGTH_MIN_M), ZONE_LENGTH_MAX_M)
    return indexes[len(indexes) // 2], round(length, 1)


def zone_to_marker(zone: Zone, editor: EditorOutline) -> dict:
    """One stored zone as a marker dict for the editor."""
    center, length = zone_position(zone, editor)
    return {
        "id": str(zone.id),
        "label": zone.label,
        "threshold_g": zone.threshold_g,
        "center_index": center,
        "length_m": length,
        "radius_m": round(marker_radius(center, length, editor), 1) if center is not None else None,
    }


def markers_for_track(track: Track, editor: EditorOutline) -> List[dict]:
    """The track's active zones as markers, in lap order (unplaced ones last)."""
    markers = [zone_to_marker(z, editor) for z in track.zones.filter(is_active=True)]
    return sorted(markers, key=lambda m: (m["center_index"] is None, m["center_index"] or 0))


def suggest_markers(editor: EditorOutline, markers: List[dict]) -> List[dict]:
    """The tightest point of each bend (where g is highest at a given speed), with its radius."""
    found = find_corners(Outline(frame=editor.frame, points=editor.points, spacing_m=editor.spacing_m))
    marked = set()
    for m in markers:
        if m["center_index"] is not None:
            marked.update(segment_indexes(m["center_index"], m["length_m"], editor))
    return [{
        "center_index": c.apex_index,
        "radius_m": round(c.tightest_radius_m, 1),
        "suggested_name": f"Turn {n}",
        "start_index": c.start_index,
        "end_index": c.end_index,
        "already_marked": c.apex_index in marked,
    } for n, c in enumerate(found, start=1)]


def validate_markers(track: Track, editor: EditorOutline, raw_markers) -> List[dict]:
    """Check every marker; returns cleaned markers or raises CornerEditError with a clear message."""
    if not isinstance(raw_markers, list) or len(raw_markers) > MAX_MARKERS:
        raise CornerEditError(f"markers must be a list of at most {MAX_MARKERS} corners.")
    low, high = track.min_threshold_g, track.max_threshold_g
    cleaned, seen_labels, covered = [], {}, {}
    for position, item in enumerate(raw_markers, start=1):
        if not isinstance(item, dict):
            raise CornerEditError(f"Corner {position} is not valid.")
        label = item.get("label").strip() if isinstance(item.get("label"), str) else ""
        if not label or len(label) > MAX_LABEL_LENGTH or CONTROL_CHARS.search(label):
            raise CornerEditError(f"Corner {position} needs a name of 1 to {MAX_LABEL_LENGTH} characters.")
        if label.lower().startswith("straight"):
            raise CornerEditError(f"'{label}': a corner name cannot start with 'Straight' (that word means no corner).")
        if label.lower() in seen_labels:
            raise CornerEditError(f"Two corners are named '{label}'. Each corner needs a different name.")
        seen_labels[label.lower()] = True
        limit, length, center = item.get("threshold_g"), item.get("length_m", ZONE_LENGTH_DEFAULT_M), item.get("center_index")
        if isinstance(limit, bool) or not isinstance(limit, (int, float)) or not (low <= limit <= high):
            raise CornerEditError(f"'{label}': the limit must be from {low} to {high} g.")
        if isinstance(length, bool) or not isinstance(length, (int, float)) or not (ZONE_LENGTH_MIN_M <= length <= ZONE_LENGTH_MAX_M):
            raise CornerEditError(f"'{label}': the zone length must be from {ZONE_LENGTH_MIN_M:g} to {ZONE_LENGTH_MAX_M:g} m.")
        if isinstance(center, bool) or not isinstance(center, int) or not (0 <= center < editor.count):
            raise CornerEditError(f"'{label}' is not placed on the outline. Click the outline to place it.")
        zone_id = item.get("id")
        if zone_id is not None and not isinstance(zone_id, str):
            raise CornerEditError(f"'{label}': bad corner id.")
        for index in segment_indexes(center, length, editor):
            if index in covered and covered[index] != label:
                raise CornerEditError(f"'{label}' overlaps '{covered[index]}'. Shorten a zone or move a marker.")
            covered[index] = label
        cleaned.append({"id": zone_id, "label": label, "threshold_g": round(float(limit), 3),
                        "length_m": round(float(length), 1), "center_index": center})
    return cleaned


def gps_range_for(marker: dict, editor: EditorOutline) -> dict:
    """The zone segment (start, end, centre) of a marker, as stored in Zone.gps_range."""
    indexes = segment_indexes(marker["center_index"], marker["length_m"], editor)
    return {
        "start": editor.lat_lng(indexes[0]),
        "end": editor.lat_lng(indexes[-1]),
        "center": editor.lat_lng(marker["center_index"]),
        "length_m": marker["length_m"],
    }


@transaction.atomic
def save_markers(track: Track, editor: EditorOutline, user, cleaned: List[dict]) -> Dict[str, int]:
    """Create, update and retire zones so the track's active zones match the markers."""
    existing = {str(z.id): z for z in track.zones.filter(is_active=True).select_for_update()}
    kept, counts = set(), {"created": 0, "updated": 0, DELETED: 0, DEACTIVATED: 0}
    for marker in cleaned:
        zone = existing.get(marker["id"]) if marker["id"] else None
        if marker["id"] and zone is None:
            raise CornerEditError(f"'{marker['label']}': that corner no longer exists. Reload and try again.", 409)
        shape = gps_range_for(marker, editor)
        if zone is None:
            Zone.objects.create(track=track, label=marker["label"], threshold_g=marker["threshold_g"],
                                corner_type=Zone.CornerType.OTHER, gps_range=shape)
            counts["created"] += 1
            continue
        kept.add(marker["id"])
        zone.label, zone.gps_range = marker["label"], shape
        zone.save(update_fields=["label", "gps_range"])
        set_zone_limit(zone, marker["threshold_g"], user)
        counts["updated"] += 1
    for zone_id, zone in existing.items():
        if zone_id not in kept:
            counts[retire_zone(zone)] += 1
    return counts
