"""
Trackside — Track import views (Admin and Coach only).

POST /api/tracks/import/preview/ reads an uploaded RaceChrono CSV or VBO file
and returns what the import would create. It never saves anything.
"""

from rest_framework.generics import GenericAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from accounts.permissions import IsAdminOrCoach
from tracks.importing.errors import TrackImportError
from tracks.importing.preview import build_preview
from tracks.importing.upload import parse_uploaded_track_file
from tracks.throttles import TrackImportPreviewThrottle


class TrackImportPreviewView(GenericAPIView):
    """Upload a session export and get a preview of the track it describes."""

    permission_classes = [IsAdminOrCoach]
    parser_classes = [MultiPartParser]
    throttle_classes = [TrackImportPreviewThrottle]

    def post(self, request):
        """Parse the uploaded file and return the preview, or a clear 4xx error."""
        try:
            parsed = parse_uploaded_track_file(request.FILES.get("file"))
            preview = build_preview(parsed)
        except TrackImportError as error:
            return Response({"detail": error.message}, status=error.status_code)
        return Response(preview)
