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

    Computes heading-change zone-boundary candidate corners from real GPS bearing math,
    averages multi-lap GPS noise, and returns suggested corner zones for coach/admin confirmation.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        import math
        from django.utils import timezone
        from rest_framework.response import Response
        from rest_framework import status
        from django.shortcuts import get_object_or_404
        from tracks.models import Track

        track = get_object_or_404(Track, pk=pk)

        payload = request.data
        if isinstance(payload, list):
            laps = [payload]
        elif isinstance(payload, dict):
            if "laps" in payload and isinstance(payload["laps"], list):
                laps = payload["laps"]
            elif "points" in payload and isinstance(payload["points"], list):
                laps = [payload["points"]]
            else:
                laps = []
        else:
            laps = []

        # Filter out empty or invalid laps
        valid_laps = []
        for lap in laps:
            if isinstance(lap, list):
                valid_pts = [p for p in lap if isinstance(p, dict) and "lat" in p and "lng" in p]
                if valid_pts:
                    valid_laps.append(valid_pts)

        if not valid_laps:
            return Response(
                {"detail": "A proper survey lap with at least 3 valid GPS points is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Average GPS coordinates across multiple survey laps to reduce noise
        max_len = max(len(l) for l in valid_laps)
        avg_points = []
        for i in range(max_len):
            pts = [l[i] for l in valid_laps if i < len(l)]
            if pts:
                avg_lat = sum(float(p["lat"]) for p in pts) / len(pts)
                avg_lng = sum(float(p["lng"]) for p in pts) / len(pts)
                avg_points.append({"lat": round(avg_lat, 6), "lng": round(avg_lng, 6)})

        if len(avg_points) < 3:
            return Response(
                {"detail": "A proper survey lap with at least 3 valid GPS points is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Compute compass bearings (headings) between consecutive GPS points
        headings = []
        for i in range(len(avg_points) - 1):
            p1, p2 = avg_points[i], avg_points[i + 1]
            lat1, lng1 = math.radians(p1["lat"]), math.radians(p1["lng"])
            lat2, lng2 = math.radians(p2["lat"]), math.radians(p2["lng"])
            d_lng = lng2 - lng1
            y = math.sin(d_lng) * math.cos(lat2)
            x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lng)
            bearing = (math.degrees(math.atan2(y, x)) + 360.0) % 360.0
            headings.append(bearing)

        # Compute turn angles (heading change between consecutive segments)
        turn_angles = []
        for i in range(len(headings) - 1):
            delta = (headings[i + 1] - headings[i] + 180.0) % 360.0 - 180.0
            turn_angles.append(delta)

        # Scan heading changes to detect sustained turning corners (candidate zones)
        candidate_zones = []
        i = 0
        while i < len(turn_angles):
            abs_turn = abs(turn_angles[i])

            # Check if this point starts a turning maneuver (sustained >= 12° or cumulative >= 20°)
            is_turn_start = abs_turn >= 12.0
            if not is_turn_start and i + 1 < len(turn_angles):
                is_turn_start = (abs_turn + abs(turn_angles[i + 1])) >= 20.0

            if is_turn_start:
                start_pt_idx = i
                end_pt_idx = i + 2
                cum_turn = abs_turn

                # Extend corner region while turning continues
                j = i + 1
                while j < len(turn_angles) and abs(turn_angles[j]) >= 8.0:
                    cum_turn += abs(turn_angles[j])
                    end_pt_idx = j + 2
                    j += 1

                # Estimate safe G-force threshold from corner curvature/sharpness
                if cum_turn >= 75.0:
                    estimated_threshold = 1.15  # Tight hairpin
                elif cum_turn >= 35.0:
                    estimated_threshold = 1.20  # Chicane / Medium turn
                else:
                    estimated_threshold = 1.25  # Gentle sweeper

                candidate_zones.append(
                    {
                        "order_number": len(candidate_zones) + 1,
                        "suggested_label": f"Zone {len(candidate_zones) + 1}",
                        "start_lat": avg_points[start_pt_idx]["lat"],
                        "start_lng": avg_points[start_pt_idx]["lng"],
                        "end_lat": avg_points[min(end_pt_idx, len(avg_points) - 1)]["lat"],
                        "end_lng": avg_points[min(end_pt_idx, len(avg_points) - 1)]["lng"],
                        "max_g_threshold": estimated_threshold,
                    }
                )
                i = max(j, i + 1)
            else:
                i += 1

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

