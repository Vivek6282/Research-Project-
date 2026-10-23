"""
Trackside — Draw a track on the map (Admin and Coach only).

POST /api/tracks/draw/preview/ takes the points clicked on the map and returns what saving them would create
(the smooth outline and the corners found on it), in the same shape as an import preview. It saves nothing.
POST /api/tracks/draw/confirm/ takes the same points plus the map name, corner names and limits, builds the
outline again on the server and saves the Track and its Zones. The shape always comes from the clicked points,
never from an outline sent by the browser.
"""

import json

from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from accounts.permissions import IsAdminOrCoach
from tracks.importing.confirm import check_track_name, read_corner_choices, save_imported_track
from tracks.importing.corners import find_corners
from tracks.importing.drawn import build_drawn_outline, parse_drawn_points
from tracks.importing.errors import TrackImportError
from tracks.importing.preview import build_preview
from tracks.importing.radius_option import read_radius_option
from tracks.serializers import TrackSerializer
from tracks.throttles import TrackDrawThrottle


def body_value(request, key):
    """One value of a JSON body (a body that is not an object has none)."""
    return request.data.get(key) if isinstance(request.data, dict) else None


class TrackDrawPreviewView(GenericAPIView):
    """Send the clicked points and get a preview of the track they make."""

    permission_classes = [IsAdminOrCoach]
    throttle_classes = [TrackDrawThrottle]

    def post(self, request):
        """Check the points, build the outline and answer with the preview, or a clear 4xx error."""
        try:
            parsed = parse_drawn_points(body_value(request, "points"))
            outline = build_drawn_outline(parsed.samples)
            preview = build_preview(parsed, read_radius_option(body_value(request, "corner_radius_m")), outline)
        except TrackImportError as error:
            return Response({"detail": error.message}, status=error.status_code)
        return Response(preview)


class TrackDrawConfirmView(GenericAPIView):
    """Send the same points with the map name, corner names and limits to save the drawn track."""

    permission_classes = [IsAdminOrCoach]
    throttle_classes = [TrackDrawThrottle]

    def post(self, request):
        """Rebuild the outline from the points, check the choices, then save the Track and its Zones."""
        try:
            name = check_track_name(body_value(request, "name"))
            parsed = parse_drawn_points(body_value(request, "points"))
            outline = build_drawn_outline(parsed.samples)
            corners = find_corners(outline, read_radius_option(body_value(request, "corner_radius_m")))
            raw_choices = body_value(request, "corners")
            choices = read_corner_choices(json.dumps(raw_choices) if isinstance(raw_choices, list) else raw_choices, len(corners))
            track = save_imported_track(request.user, name, parsed, outline, corners, choices)
        except TrackImportError as error:
            return Response({"detail": error.message}, status=error.status_code)
        return Response(TrackSerializer(track).data, status=201)
