"""
Trackside — Track import views (Admin and Coach only).

POST /api/tracks/import/preview/ reads an uploaded RaceChrono CSV or VBO file
and returns what the import would create. It never saves anything.
POST /api/tracks/import/confirm/ takes the same file plus the user's map name,
corner names and limits, and saves the Track and its Zones.
"""

from rest_framework.generics import GenericAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from accounts.permissions import IsAdminOrCoach
from tracks.importing.confirm import check_track_name, read_corner_choices, save_imported_track
from tracks.importing.corners import find_corners
from tracks.importing.errors import TrackImportError
from tracks.importing.outline import build_outline
from tracks.importing.preview import build_preview
from tracks.importing.radius_option import read_radius_option
from tracks.importing.upload import parse_uploaded_track_file
from tracks.serializers import TrackSerializer
from tracks.throttles import TrackImportConfirmThrottle, TrackImportPreviewThrottle


class TrackImportPreviewView(GenericAPIView):
    """Upload a session export and get a preview of the track it describes."""

    permission_classes = [IsAdminOrCoach]
    parser_classes = [MultiPartParser]
    throttle_classes = [TrackImportPreviewThrottle]

    def post(self, request):
        """Parse the uploaded file and return the preview, or a clear 4xx error."""
        try:
            parsed = parse_uploaded_track_file(request.FILES.get("file"))
            preview = build_preview(parsed, read_radius_option(request.data.get("corner_radius_m")))
        except TrackImportError as error:
            return Response({"detail": error.message}, status=error.status_code)
        return Response(preview)


class TrackImportConfirmView(GenericAPIView):
    """Upload the same file again with the user's map name, corner names and limits to save the map."""

    permission_classes = [IsAdminOrCoach]
    parser_classes = [MultiPartParser]
    throttle_classes = [TrackImportConfirmThrottle]

    def post(self, request):
        """Re-read the file, check the user's choices, then save the Track and its Zones."""
        try:
            name = check_track_name(request.data.get("name"))
            parsed = parse_uploaded_track_file(request.FILES.get("file"))
            outline = build_outline(parsed.samples)
            corners = find_corners(outline, read_radius_option(request.data.get("corner_radius_m")))
            choices = read_corner_choices(request.data.get("corners"), len(corners))
            track = save_imported_track(request.user, name, parsed, outline, corners, choices)
        except TrackImportError as error:
            return Response({"detail": error.message}, status=error.status_code)
        return Response(TrackSerializer(track).data, status=201)
