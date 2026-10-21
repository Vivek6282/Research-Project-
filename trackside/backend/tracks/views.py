"""
Trackside — Tracks views.

Track and Zone CRUD with role-based access:
- Admin: full CRUD on tracks and zones
- Coach/Driver: read-only access to tracks and zones
"""

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAdmin, IsAdminOrCoach
from drivers.models import DriverZoneThreshold
from tracks.models import Track, Zone, ZoneThresholdHistory
from tracks.demo_circuit_setup import ensure_demo_circuit
from tracks.limit_history import record_initial_limit
from tracks.zone_retirement import DEACTIVATED, retire_zone
from tracks.serializers import TrackSerializer, ZoneSerializer, ZoneThresholdHistorySerializer

BUILTIN_LOCKED_MESSAGE = "The built-in Demo Circuit is locked: it cannot be edited, archived or deleted."


def builtin_locked_response():
    """The 409 answer for any change to the built-in track."""
    return Response({"detail": BUILTIN_LOCKED_MESSAGE}, status=409)


def track_lock_response(track: Track):
    """A 409 Response when the track's corners must not change (built-in or archived), else None."""
    if track.is_builtin:
        return builtin_locked_response()
    if track.is_archived:
        return Response({"detail": "This map is archived. Restore it before changing its corners."}, status=409)
    return None


def track_has_history(track: Track) -> bool:
    """True when sessions or driver thresholds exist for the track, so deleting would lose history."""
    return (track.sessions.exists()
            or DriverZoneThreshold.objects.filter(zone__track=track).exists())


class TrackListCreateView(generics.ListCreateAPIView):
    """
    GET /api/tracks/ — list active tracks (any authenticated user);
        ?archived=only lists archived ones, ?archived=all lists both
    POST /api/tracks/ — create a new track (Admin only)
    """

    serializer_class = TrackSerializer

    def get_permissions(self):
        """Admin can create, anyone authenticated can list."""
        if self.request.method == "POST":
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """Active tracks by default (archived ones are hidden from pickers); see ?archived."""
        queryset = Track.objects.prefetch_related("zones")
        archived = self.request.query_params.get("archived")
        if archived == "only":
            return queryset.filter(is_archived=True)
        if archived == "all":
            return queryset
        return queryset.filter(is_archived=False)

    def perform_create(self, serializer):
        """Record who created the track."""
        serializer.save(created_by=self.request.user)


class TrackDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/tracks/<uuid>/ — retrieve a track
    PUT/PATCH /api/tracks/<uuid>/ — update a track (Admin only)
    DELETE /api/tracks/<uuid>/ — Admin or Coach. A track with sessions (or driver
        thresholds) is archived and keeps its history; a never-used track is deleted.
    The built-in track answers 409 to every change. Archived tracks can still be read.
    """

    serializer_class = TrackSerializer

    def get_permissions(self):
        """Admin edits, Admin or Coach archives/deletes, anyone authenticated can view."""
        if self.request.method in ("PUT", "PATCH"):
            return [IsAdmin()]
        if self.request.method == "DELETE":
            return [IsAdminOrCoach()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """Return all tracks (archived too) with zones prefetched."""
        return Track.objects.prefetch_related("zones").all()

    def update(self, request, *args, **kwargs):
        """Refuse edits to the built-in track."""
        if self.get_object().is_builtin:
            return builtin_locked_response()
        return super().update(request, *args, **kwargs)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """Archive a track that has history, delete one that never was used, refuse the built-in."""
        track = self.get_object()
        if track.is_builtin:
            return builtin_locked_response()
        if track_has_history(track):
            track.is_archived = True
            track.save(update_fields=["is_archived"])
            return Response({"detail": "Map archived. Its session history is kept.", "status": "archived"})
        track.delete()
        return Response(status=204)


class TrackRestoreView(generics.GenericAPIView):
    """POST /api/tracks/<uuid>/restore/ — bring an archived track back (Admin or Coach)."""

    permission_classes = [IsAdminOrCoach]
    serializer_class = TrackSerializer
    queryset = Track.objects.all()

    def post(self, request, pk=None):
        """Clear the archived flag; the built-in track and active tracks are refused."""
        track = self.get_object()
        if track.is_builtin:
            return builtin_locked_response()
        if not track.is_archived:
            return Response({"detail": "This map is not archived."}, status=400)
        track.is_archived = False
        track.save(update_fields=["is_archived"])
        return Response(TrackSerializer(track).data)


class ZoneListCreateView(generics.ListCreateAPIView):
    """
    GET /api/tracks/<uuid>/zones/ — list zones for a track (any signed-in user)
    POST /api/tracks/<uuid>/zones/ — add a zone (Admin or Coach). Refused with 409 on the built-in
        and on archived tracks; name, limit and gps_range are checked by ZoneSerializer.
    """

    serializer_class = ZoneSerializer

    def get_permissions(self):
        """Admin or Coach may add zones; any signed-in user can read them."""
        if self.request.method == "POST":
            return [IsAdminOrCoach()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """Active zones of the track in the URL (removed corners are hidden from new sessions)."""
        track_id = self.kwargs.get("track_pk")
        return Zone.objects.filter(track_id=track_id, is_active=True)

    def get_serializer_context(self):
        """Give the serializer the track so it can check the limit against the track's range."""
        context = super().get_serializer_context()
        if self.request.method == "POST":
            context["track"] = get_object_or_404(Track, pk=self.kwargs.get("track_pk"))
        return context

    def create(self, request, *args, **kwargs):
        """Refuse locked tracks before looking at the data, then create the zone."""
        locked = track_lock_response(get_object_or_404(Track, pk=self.kwargs.get("track_pk")))
        return locked if locked else super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """Save the zone on the track from the URL and start its limit history."""
        zone = serializer.save(track_id=self.kwargs.get("track_pk"))
        record_initial_limit(zone, self.request.user)


class ZoneDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/tracks/<uuid>/zones/<uuid>/ — retrieve a zone
    PUT/PATCH/DELETE — Admin only, refused with 409 on the built-in and on archived tracks.
    DELETE keeps history: a zone with telemetry, alerts, notes or driver limits is
    deactivated instead of removed.
    """

    serializer_class = ZoneSerializer

    def get_permissions(self):
        """Admin changes zones; any signed-in user can read them."""
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """Zones of the track in the URL."""
        track_id = self.kwargs.get("track_pk")
        return Zone.objects.filter(track_id=track_id)

    def update(self, request, *args, **kwargs):
        """Refuse changes on a locked track, otherwise save (a changed limit is written to the history)."""
        locked = track_lock_response(self.get_object().track)
        return locked if locked else super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Delete a zone with no history; deactivate one that has history; refuse on a locked track."""
        zone = self.get_object()
        locked = track_lock_response(zone.track)
        if locked:
            return locked
        outcome = retire_zone(zone)
        if outcome == DEACTIVATED:
            return Response({"detail": "Zone has history, so it was deactivated and hidden.", "status": outcome})
        return Response(status=204)


class ZoneLimitHistoryView(generics.ListAPIView):
    """GET /api/tracks/<uuid>/zones/<uuid>/limit-history/ — read-only list of limit changes (Admin/Coach)."""

    permission_classes = [IsAdminOrCoach]
    serializer_class = ZoneThresholdHistorySerializer

    def get_queryset(self):
        """History rows of one zone, newest first."""
        return ZoneThresholdHistory.objects.filter(
            zone_id=self.kwargs["pk"], zone__track_id=self.kwargs["track_pk"],
        ).select_related("changed_by")


class DemoCircuitView(generics.GenericAPIView):
    """POST /api/tracks/demo-circuit/ — make sure the built-in Demo Circuit exists, then return it (Admin/Coach)."""

    permission_classes = [IsAdminOrCoach]
    serializer_class = TrackSerializer

    def post(self, request):
        """Create the Demo Circuit and its three corners if missing (safe to call any number of times)."""
        return Response(TrackSerializer(ensure_demo_circuit()).data)


class TrackReferenceLineView(generics.GenericAPIView):
    """
    GET /api/tracks/<uuid>/reference-line/ — return the track's surveyed GPS polyline.

    Lightweight endpoint for the Live Track View panel: returns only the
    reference_line JSONB array (ordered {lat, lng} points) without loading
    zones or other nested data.  Returns null when the track hasn't been
    surveyed yet, so the frontend can show a graceful fallback.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        from rest_framework.response import Response
        from django.shortcuts import get_object_or_404

        track = get_object_or_404(Track, pk=pk)
        return Response({
            "track_id": str(track.id),
            "track_name": track.name,
            "reference_line": track.reference_line,
        })
