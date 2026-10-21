"""
Trackside — Check the user's corner names/limits and save an imported track (C5).

The file is parsed again on the server, so the saved shape and corner positions
always come from the file, never from numbers sent by the browser.
"""

import json
import re
from typing import List

from django.db import transaction
from django.utils import timezone

from tracks.importing.corners import Corner, corner_to_json
from tracks.importing.errors import TrackImportError
from tracks.importing.outline import Outline
from tracks.importing.safe_speed import LIMIT_MAX_G, LIMIT_MIN_G
from tracks.importing.samples import ParsedTrackFile, to_finite_float
from tracks.limit_history import record_initial_limit
from tracks.models import Track, Zone

MAX_LABEL_LENGTH = 40
MAX_TRACK_NAME_LENGTH = 150
MAX_CORNERS_JSON_CHARS = 50_000
CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
CHANGED_MESSAGE = "The corner list does not match the file. Run the preview again."


def clean_text(value, field: str, max_length: int) -> str:
    """Trim a required text field and check its length and characters."""
    text = value.strip() if isinstance(value, str) else ""
    if not text:
        raise TrackImportError(f"{field} is required.")
    if len(text) > max_length:
        raise TrackImportError(f"{field} can be at most {max_length} characters.")
    if CONTROL_CHARS.search(text):
        raise TrackImportError(f"{field} contains characters that are not allowed.")
    return text


def read_corner_choices(raw_json, corner_count: int) -> List[dict]:
    """Parse and check the user's per-corner labels and limits; returns them in corner order."""
    if not isinstance(raw_json, str) or len(raw_json) > MAX_CORNERS_JSON_CHARS:
        raise TrackImportError("corners must be a JSON list of {number, label, threshold_g}.")
    try:
        items = json.loads(raw_json)
    except ValueError:
        raise TrackImportError("corners is not valid JSON.")
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        raise TrackImportError("corners must be a JSON list of {number, label, threshold_g}.")
    if len(items) != corner_count or sorted(i.get("number") for i in items if isinstance(i.get("number"), int)) != list(
        range(1, corner_count + 1)
    ):
        raise TrackImportError(CHANGED_MESSAGE)

    choices = []
    for item in sorted(items, key=lambda i: i["number"]):
        number = item["number"]
        label = clean_text(item.get("label"), f"Corner {number} name", MAX_LABEL_LENGTH)
        limit = to_finite_float(str(item.get("threshold_g", "")))
        if limit is None or not (LIMIT_MIN_G <= limit <= LIMIT_MAX_G):
            raise TrackImportError(f"Corner {number} limit must be from {LIMIT_MIN_G} to {LIMIT_MAX_G} g.")
        choices.append({"label": label, "threshold_g": round(limit, 3)})
    labels = [c["label"].lower() for c in choices]
    if len(set(labels)) != len(labels):
        raise TrackImportError("Each corner needs a different name.")
    return choices


def check_track_name(raw_name) -> str:
    """Return the cleaned map name, refusing blanks and names already in use (archived ones too)."""
    name = clean_text(raw_name, "Map name", MAX_TRACK_NAME_LENGTH)
    if Track.objects.filter(name__iexact=name).exists():
        raise TrackImportError("A map with this name already exists. Choose a different name.", status_code=409)
    return name


@transaction.atomic
def save_imported_track(user, name: str, parsed: ParsedTrackFile, outline: Outline,
                        corners: List[Corner], choices: List[dict]) -> Track:
    """Create the Track and one Zone per corner, all or nothing."""
    track = Track.objects.create(
        name=name,
        reference_line=outline.as_lat_lng(),
        kart_class=Track.KartClass.SPRINT,
        source=parsed.source,
        is_builtin=False,
        surveyed_at=timezone.now(),
        created_by=user,
    )
    for number, (corner, choice) in enumerate(zip(corners, choices), start=1):
        shape = corner_to_json(number, corner, outline)
        zone = Zone.objects.create(
            track=track,
            label=choice["label"],
            corner_type=Zone.CornerType.OTHER,
            threshold_g=choice["threshold_g"],
            gps_range={"start": shape["start"], "end": shape["end"]},
        )
        record_initial_limit(zone, user)
    return track
