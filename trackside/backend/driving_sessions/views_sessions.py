"""
Trackside Driving Sessions — Session CRUD Views.
This module provides endpoints for listing, creating, retrieving, updating,
and ending driving sessions with strict role-based access scoping.
"""

from django.utils import timezone
from rest_framework import generics, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAdminOrCoach
from devices.authentication import DeviceTokenAuthentication
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
            serializer.save(driver=acting_user)
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
    - Denied (403): Driver (even if owner), other driver's device, unassigned device.
    - Denied (401): Anonymous / unauthenticated request.
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
        session_id = kwargs.get("pk") or kwargs.get("session_pk")
        try:
            session = Session.objects.get(pk=session_id)
        except (Session.DoesNotExist, ValueError):
            return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        role = getattr(user, "role", None)

        # Drivers are denied from finishing sessions directly
        if role == "driver":
            return Response(
                {"error": "Drivers are not permitted to close sessions directly."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Device tokens must be assigned to the driver who owns the session; coaches and admins can access any session
        if not can_access_session(user, session):
            return Response(
                {"error": "You do not have permission to finish this session."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Set ended_at to current time only if not already set (idempotent)
        if session.ended_at is None:
            session.ended_at = timezone.now()
            session.save(update_fields=["ended_at"])

        serializer = self.get_serializer(session)
        return Response(serializer.data, status=status.HTTP_200_OK)
