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
