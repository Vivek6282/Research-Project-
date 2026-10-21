"""
Trackside — Corner editor and duplicate endpoints (Admin and Coach only).

GET  /api/tracks/<id>/corners/     outline, markers, suggestions and limits for the editor
PUT  /api/tracks/<id>/corners/     save the markers as zones (custom, active maps only)
POST /api/tracks/<id>/duplicate/   copy a map into a new editable custom map
"""

from django.shortcuts import get_object_or_404
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from accounts.permissions import IsAdminOrCoach
from tracks.corner_editor import (
    NO_CURVE_RADIUS_M, ZONE_LENGTH_DEFAULT_M, ZONE_LENGTH_MAX_M, ZONE_LENGTH_MIN_M, CornerEditError,
    editor_outline, markers_for_track, save_markers, suggest_markers, validate_markers,
)
from tracks.duplicate import duplicate_track
from tracks.importing.safe_speed import DEFAULT_LIMIT_G
from tracks.models import Track
from tracks.serializers import TrackSerializer
from tracks.views import builtin_locked_response


def editor_payload(track: Track) -> dict:
    """Everything the corner editor needs to draw and edit one map."""
    editor = editor_outline(track)
    markers = markers_for_track(track, editor)
    editable = not track.is_builtin and not track.is_archived
    return {
        "track_id": str(track.id),
        "track_name": track.name,
        "editable": editable,
        "is_schematic": editor.is_schematic,
        "outline_version": editor.version,
        "spacing_m": round(editor.spacing_m, 3),
        "outline": [editor.lat_lng(i) for i in range(editor.count)],
        "radii": [round(r, 1) for r in editor.radii],
        "markers": markers,
        "suggestions": suggest_markers(editor, markers) if editable else [],
        "limit_range_g": {"min": track.min_threshold_g, "max": track.max_threshold_g,
                          "default": min(max(DEFAULT_LIMIT_G, track.min_threshold_g), track.max_threshold_g)},
        "zone_length_m": {"min": ZONE_LENGTH_MIN_M, "max": ZONE_LENGTH_MAX_M, "default": ZONE_LENGTH_DEFAULT_M},
        "no_curve_radius_m": NO_CURVE_RADIUS_M,
    }


class TrackCornersView(GenericAPIView):
    """Read or save the corner markers of one map."""

    permission_classes = [IsAdminOrCoach]
    serializer_class = TrackSerializer

    def get(self, request, pk=None):
        """Return the editor payload (view-only for the built-in and archived maps)."""
        track = get_object_or_404(Track, pk=pk)
        try:
            return Response(editor_payload(track))
        except CornerEditError as error:
            return Response({"detail": error.message}, status=error.status_code)

    def put(self, request, pk=None):
        """Save the markers: new ones become zones, removed ones are deleted or deactivated."""
        track = get_object_or_404(Track, pk=pk)
        if track.is_builtin:
            return builtin_locked_response()
        if track.is_archived:
            return Response({"detail": "This map is archived. Restore it before editing its corners."}, status=409)
        try:
            editor = editor_outline(track)
            if request.data.get("outline_version") != editor.version:
                raise CornerEditError("This map's outline changed since you opened it. Reload and try again.", 409)
            cleaned = validate_markers(track, editor, request.data.get("markers"))
            counts = save_markers(track, editor, request.user, cleaned)
            payload = editor_payload(track)
        except CornerEditError as error:
            return Response({"detail": error.message}, status=error.status_code)
        payload["saved"] = counts
        return Response(payload)


class TrackDuplicateView(GenericAPIView):
    """Copy a map and its corners into a new editable custom map."""

    permission_classes = [IsAdminOrCoach]
    serializer_class = TrackSerializer

    def post(self, request, pk=None):
        """Create the copy under the requested name (201), or explain what is wrong."""
        source = get_object_or_404(Track, pk=pk)
        try:
            result = duplicate_track(source, request.user, request.data.get("name"))
        except CornerEditError as error:
            return Response({"detail": error.message}, status=error.status_code)
        body = TrackSerializer(result["track"]).data
        return Response({**body, "clamped": result["clamped"], "skipped": result["skipped"]}, status=201)
