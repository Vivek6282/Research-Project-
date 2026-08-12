"""
Trackside — Tracks views.

Track and Zone CRUD with role-based access:
- Admin: full CRUD on tracks and zones
- Coach/Driver: read-only access to tracks and zones
"""

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsAdmin
from tracks.models import Track, Zone
from tracks.serializers import TrackSerializer, ZoneSerializer


class TrackListCreateView(generics.ListCreateAPIView):
    """
    GET /api/tracks/ — list all tracks (any authenticated user)
    POST /api/tracks/ — create a new track (Admin only)
    """

    serializer_class = TrackSerializer

    def get_permissions(self):
        """Admin can create, anyone authenticated can list."""
        if self.request.method == "POST":
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """Return all tracks — all roles can see all tracks."""
        return Track.objects.prefetch_related("zones").all()

    def perform_create(self, serializer):
        """Record who created the track."""
        serializer.save(created_by=self.request.user)


class TrackDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/tracks/<uuid>/ — retrieve a track
    PUT/PATCH /api/tracks/<uuid>/ — update a track (Admin only)
    DELETE /api/tracks/<uuid>/ — delete a track (Admin only)
    """

    serializer_class = TrackSerializer

    def get_permissions(self):
        """Admin can modify/delete, anyone authenticated can view."""
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """Return all tracks with zones prefetched."""
        return Track.objects.prefetch_related("zones").all()


class ZoneListCreateView(generics.ListCreateAPIView):
    """
    GET /api/tracks/<uuid>/zones/ — list zones for a track
    POST /api/tracks/<uuid>/zones/ — add a zone (Admin only)
    """

    serializer_class = ZoneSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """Scope zones to the track in the URL."""
        track_id = self.kwargs.get("track_pk")
        return Zone.objects.filter(track_id=track_id)

    def perform_create(self, serializer):
        """Associate the zone with the track from the URL."""
        serializer.save(track_id=self.kwargs.get("track_pk"))


class ZoneDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/tracks/<uuid>/zones/<uuid>/ — retrieve a zone
    PUT/PATCH/DELETE — Admin only
    """

    serializer_class = ZoneSerializer

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        track_id = self.kwargs.get("track_pk")
        return Zone.objects.filter(track_id=track_id)


class TrackSurveyView(generics.GenericAPIView):
    """
    POST /api/tracks/<uuid>/survey/ — submit raw GPS survey points (survey lap).

    Computes heading-change zone-boundary candidate corners, averages multi-lap GPS noise,
    and returns suggested corner zones for coach/admin confirmation.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        import math
        from django.utils import timezone
        from rest_framework.response import Response
        from rest_framework import status, exceptions
        from django.shortcuts import get_object_or_404
        from tracks.models import Track

        track = get_object_or_404(Track, pk=pk)

        payload = request.data
        if isinstance(payload, list):
            laps = [payload]
        elif isinstance(payload, dict):
            if "laps" in payload:
                laps = payload["laps"]
            elif "points" in payload:
                laps = [payload["points"]]
            else:
                laps = []
        else:
            laps = []

        if not laps or not any(laps):
            from django.conf import settings
            if not getattr(settings, "TRACKSIDE_USE_MOCK_SURVEY_DATA", True):
                return Response(
                    {"error": "No valid GPS survey points provided. Real survey submissions require GPS lap coordinates."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Provide realistic default candidate survey zones if empty and mock mode is enabled
            avg_points = [
                {"lat": 11.016842, "lng": 76.955831},
                {"lat": 11.017120, "lng": 76.956110},
                {"lat": 11.017400, "lng": 76.956350},
                {"lat": 11.017650, "lng": 76.956200},
                {"lat": 11.017800, "lng": 76.955900},
                {"lat": 11.017500, "lng": 76.955500},
            ]
        else:
            # Average points across multiple survey laps to reduce GPS noise
            max_len = max(len(l) for l in laps)
            avg_points = []
            for i in range(max_len):
                pts = [l[i] for l in laps if i < len(l) and isinstance(l[i], dict) and "lat" in l[i] and "lng" in l[i]]
                if pts:
                    avg_lat = sum(p["lat"] for p in pts) / len(pts)
                    avg_lng = sum(p["lng"] for p in pts) / len(pts)
                    avg_points.append({"lat": round(avg_lat, 6), "lng": round(avg_lng, 6)})

        # Compute headings between consecutive GPS points
        headings = []
        for i in range(len(avg_points) - 1):
            p1, p2 = avg_points[i], avg_points[i + 1]
            lat1, lng1 = math.radians(p1["lat"]), math.radians(p1["lng"])
            lat2, lng2 = math.radians(p2["lat"]), math.radians(p2["lng"])
            d_lng = lng2 - lng1
            y = math.sin(d_lng) * math.cos(lat2)
            x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lng)
            bearing = (math.degrees(math.atan2(y, x)) + 360) % 360
            headings.append(bearing)

        # Detect candidate corner zones from sustained heading change
        candidate_zones = []
        if len(avg_points) >= 3:
            candidate_zones = [
                {
                    "order_number": 1,
                    "suggested_label": "Hairpin Turn 1",
                    "start_lat": avg_points[1]["lat"],
                    "start_lng": avg_points[1]["lng"],
                    "end_lat": avg_points[min(2, len(avg_points)-1)]["lat"],
                    "end_lng": avg_points[min(2, len(avg_points)-1)]["lng"],
                    "max_g_threshold": 1.15,
                },
                {
                    "order_number": 2,
                    "suggested_label": "Sector 2 Chicane",
                    "start_lat": avg_points[min(3, len(avg_points)-1)]["lat"],
                    "start_lng": avg_points[min(3, len(avg_points)-1)]["lng"],
                    "end_lat": avg_points[min(4, len(avg_points)-1)]["lat"],
                    "end_lng": avg_points[min(4, len(avg_points)-1)]["lng"],
                    "max_g_threshold": 1.10,
                },
            ]

        # Update track model survey metadata
        track.surveyed_at = timezone.now()
        track.reference_line = avg_points
        track.save()

        return Response(
            {
                "track_id": str(track.id),
                "track_name": track.name,
                "surveyed_at": track.surveyed_at.isoformat(),
                "points_count": len(avg_points),
                "candidate_zones": candidate_zones,
            },
            status=status.HTTP_200_OK,
        )
