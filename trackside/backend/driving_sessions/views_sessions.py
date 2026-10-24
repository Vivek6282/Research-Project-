"""
Trackside Driving Sessions — Session CRUD Views.
This module provides endpoints for listing, creating, retrieving, updating,
and ending driving sessions with strict role-based access scoping.
"""

from rest_framework import generics, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAdminOrCoach
from devices.authentication import DeviceTokenAuthentication
from driving_sessions.session_close import close_session_if_open
from driving_sessions.access import sessions_visible_to, can_access_session
from driving_sessions.models import Session
from driving_sessions.serializers import SessionSerializer
from driving_sessions.views_telemetry import DeviceTelemetryRateThrottle


class SessionListCreateView(generics.ListCreateAPIView):
    """
    GET /api/sessions/ — list sessions scoped by role.
    POST /api/sessions/ — driver starts a new driving session.

    Security:
    - Drivers only see their own sessions.
    - Devices only see sessions for their assigned driver.
    - Coaches and admins see all sessions.
    """

    serializer_class = SessionSerializer

    def get_permissions(self):
        """
        Returns permissions required for this endpoint.
        Input: None.
        Output: List with IsAuthenticated instance.
        """
        return [IsAuthenticated()]

    def get_queryset(self):
        """
        Returns sessions visible to the authenticated user.
        Input: None (uses request.user).
        Output: Scoped Session QuerySet with driver and track pre-fetched.
        """
        return sessions_visible_to(self.request.user).select_related("driver", "track")

    def perform_create(self, serializer):
        """
        Associates the session with the authenticated driver if the user is a driver.
        Input: Validated Session serializer.
        Output: None.
        """
        acting_user = self.request.user
        if acting_user.role == "driver":
            # A driver's own session: they cannot pick another driver or mark their own goal as passed
            serializer.save(driver=acting_user, goal_passed=None)
        else:
            serializer.save()


class SessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/sessions/<uuid>/ — retrieve session details.
    PUT/PATCH/DELETE — update or terminate session (Admin or Coach only).

    Security:
    - Retrieval is scoped to authorized sessions.
    - Mutations are restricted to coaches and admins via IsAdminOrCoach.
    """

    serializer_class = SessionSerializer

    def get_permissions(self):
        """
        Enforces Admin/Coach role for mutations while allowing authenticated drivers to view.
        Input: None.
        Output: List of permission instances.
        """
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [IsAdminOrCoach()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """
        Returns sessions visible to the user to prevent unauthorized access by UUID guess.
        Input: None.
        Output: Scoped Session QuerySet.
        """
        return sessions_visible_to(self.request.user)


class SessionFinishView(generics.GenericAPIView):
    """
    POST /api/sessions/<uuid>/finish/ — concludes an active driving session.

    Security & Access Rules:
    - Allowed: Admin, Coach, and a device token whose assigned driver owns this session.
    - Denied (403): Driver (even if owner) before lookup.
    - Denied (403): Anonymous / unauthenticated request (SessionAuthentication returns 403).
    - Denied (404): Nonexistent or inaccessible session (identical response avoids ID enumeration).
    - Idempotent: Sets ended_at = now only if currently null; second call returns 200 without altering ended_at.
    - Authentication: SessionAuthentication and DeviceTokenAuthentication.
    - Throttling: DeviceTelemetryRateThrottle (device_telemetry scope).
    """

    authentication_classes = [SessionAuthentication, DeviceTokenAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [DeviceTelemetryRateThrottle]
    throttle_scope = "device_telemetry"
    serializer_class = SessionSerializer

    def post(self, request, *args, **kwargs):
        """
        Marks the session ended_at timestamp if null, or retains existing timestamp if already ended.
        Input: session pk via URL kwargs.
        Output: HTTP 200 with updated session serializer data, or 403/404 on access failure.
        """
        user = request.user
        role = getattr(user, "role", None)

        # Drivers are denied from finishing sessions directly before any lookup
        if role == "driver":
            return Response(
                {"error": "Drivers are not permitted to close sessions directly."},
                status=status.HTTP_403_FORBIDDEN,
            )

        session_id = kwargs.get("pk") or kwargs.get("session_pk")
        try:
            session = Session.objects.get(pk=session_id)
        except (Session.DoesNotExist, ValueError):
            return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

        # Device tokens must be assigned to the driver who owns the session; coaches and admins can access any session.
        # If the caller may not access this session, return 404 with identical body to avoid leaking existence.
        if not can_access_session(user, session):
            return Response(
                {"error": "Session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Atomically set ended_at to current time only if currently null.
        # This prevents race conditions where concurrent calls might both write and alter the timestamp.
        close_session_if_open(session.pk)
        session.refresh_from_db()

        serializer = self.get_serializer(session)
        return Response(serializer.data, status=status.HTTP_200_OK)
