"""Trackside — Duplicate a map (built-in or custom) into a new, editable custom map."""

from typing import Dict, List

from django.db import transaction
from django.utils import timezone

from tracks.corner_editor import CornerEditError, editor_outline, gps_range_for, markers_for_track
from tracks.importing.confirm import check_track_name
from tracks.importing.errors import TrackImportError
from tracks.limit_history import record_initial_limit
from tracks.models import Track, Zone


@transaction.atomic
def duplicate_track(source: Track, user, raw_name) -> Dict[str, object]:
    """Copy the outline and placed corners of `source` into a new sprint-class custom track.

    Limits are kept, except that a limit outside the new track's allowed range is moved to
    the nearest allowed value and reported in `clamped` (the demo's Sweeper is 1.55 g).
    """
    try:
        name = check_track_name(raw_name)
    except TrackImportError as error:
        raise CornerEditError(error.message, error.status_code)
    editor = editor_outline(source)
    new_track = Track.objects.create(
        name=name,
        reference_line=[editor.lat_lng(i) for i in range(editor.count)],
        kart_class=Track.KartClass.SPRINT,
        source=Track.Source.MANUAL,
        is_builtin=False,
        surveyed_at=timezone.now(),
        created_by=user,
    )
    low, high = new_track.min_threshold_g, new_track.max_threshold_g
    types = {z.label: z.corner_type for z in source.zones.filter(is_active=True)}
    clamped: List[dict] = []
    skipped: List[str] = []
    for marker in markers_for_track(source, editor):
        if marker["center_index"] is None:
            skipped.append(marker["label"])
            continue
        limit = min(max(marker["threshold_g"], low), high)
        if limit != marker["threshold_g"]:
            clamped.append({"label": marker["label"], "from_g": marker["threshold_g"], "to_g": limit})
        zone = Zone.objects.create(
            track=new_track, label=marker["label"], threshold_g=limit,
            corner_type=types.get(marker["label"], Zone.CornerType.OTHER),
            gps_range=gps_range_for(marker, editor),
        )
        record_initial_limit(zone, user)
    return {"track": new_track, "clamped": clamped, "skipped": skipped}
