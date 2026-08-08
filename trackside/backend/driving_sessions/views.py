"""
Trackside — Sessions views.

Role-based session, telemetry, alert, biometric, and note access:
- Coach: sees sessions for drivers they manage, can create notes
- Driver: sees only their own sessions
- Admin: sees everything

Requirement #3 (IDOR): every queryset is scoped to what the user is
allowed to see. Drivers can never access another driver's data.
"""

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAdminOrCoach, IsCoach
from driving_sessions.models import (
    Session, Telemetry, Alert, BiometricReading, SessionNote,
)
from driving_sessions.serializers import (
    SessionSerializer, TelemetrySerializer, AlertSerializer,
    BiometricReadingSerializer, SessionNoteSerializer,
)


class SessionListCreateView(generics.ListCreateAPIView):
    """
    GET /api/sessions/ — list sessions (scoped by role)
    POST /api/sessions/ — create a session (driver starts a session)
    """

    serializer_class = SessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Requirement #3: scope sessions by role.
        Drivers see only their own sessions — never another driver's.
        """
        user = self.request.user
        queryset = Session.objects.select_related("driver", "track")

        if user.role == "admin":
            return queryset.all()
        if user.role == "coach":
            # Coaches see all sessions (they need to review any driver)
            return queryset.all()
        # Drivers see only their own sessions
        return queryset.filter(driver=user)

    def perform_create(self, serializer):
        """Auto-set the driver to the current user if they're a driver."""
        if self.request.user.role == "driver":
            serializer.save(driver=self.request.user)
        else:
            serializer.save()


class SessionDetailView(generics.RetrieveUpdateAPIView):
    """
    GET /api/sessions/<uuid>/ — retrieve session details
    PATCH /api/sessions/<uuid>/ — update session (end it, set goal result)
    """

    serializer_class = SessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Requirement #3: same role-based scoping as the list view."""
        user = self.request.user
        queryset = Session.objects.select_related("driver", "track")

        if user.role == "admin":
            return queryset.all()
        if user.role == "coach":
            return queryset.all()
        return queryset.filter(driver=user)


class TelemetryListCreateView(generics.ListCreateAPIView):
    """
    GET /api/sessions/<uuid>/telemetry/ — list telemetry for a session
    POST /api/sessions/<uuid>/telemetry/ — ingest telemetry data

    The POST endpoint is shaped to accept data from the IoT devices
    (or mocked data for now) so hardware can be connected later
    without an API redesign.
    """

    serializer_class = TelemetrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Scope telemetry to the session in the URL."""
        session_id = self.kwargs.get("session_pk")
        user = self.request.user

        # Verify the user can access this session first
        if user.role == "driver":
            return Telemetry.objects.filter(
                session_id=session_id,
                session__driver=user,
            )
        return Telemetry.objects.filter(session_id=session_id)

    def perform_create(self, serializer):
        serializer.save(session_id=self.kwargs.get("session_pk"))


class AlertListView(generics.ListAPIView):
    """
    GET /api/sessions/<uuid>/alerts/ — list alerts for a session

    Read-only — alerts are created by the system when thresholds
    are exceeded, not directly by API users.
    """

    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Scope alerts to the session and verify access."""
        session_id = self.kwargs.get("session_pk")
        user = self.request.user

        if user.role == "driver":
            return Alert.objects.filter(
                session_id=session_id,
                session__driver=user,
            ).select_related("zone")
        return Alert.objects.filter(
            session_id=session_id,
        ).select_related("zone")


class BiometricListCreateView(generics.ListCreateAPIView):
    """
    GET /api/sessions/<uuid>/biometrics/ — list biometric readings
    POST /api/sessions/<uuid>/biometrics/ — ingest biometric data
    """

    serializer_class = BiometricReadingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        session_id = self.kwargs.get("session_pk")
        user = self.request.user

        if user.role == "driver":
            return BiometricReading.objects.filter(
                session_id=session_id,
                session__driver=user,
            )
        return BiometricReading.objects.filter(session_id=session_id)

    def perform_create(self, serializer):
        serializer.save(session_id=self.kwargs.get("session_pk"))


class SessionNoteListCreateView(generics.ListCreateAPIView):
    """
    GET /api/sessions/<uuid>/notes/ — list notes for a session
    POST /api/sessions/<uuid>/notes/ — add a note (Coach only)
    """

    serializer_class = SessionNoteSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsCoach()]
        return [IsAuthenticated()]

    def get_queryset(self):
        session_id = self.kwargs.get("session_pk")
        user = self.request.user
        if user.role == "driver":
            return SessionNote.objects.filter(
                session_id=session_id,
                session__driver=user,
            ).select_related("coach", "zone")
        return SessionNote.objects.filter(
            session_id=session_id,
        ).select_related("coach", "zone")

    def perform_create(self, serializer):
        """Auto-set coach to the requesting user."""
        serializer.save(
            coach=self.request.user,
            session_id=self.kwargs.get("session_pk"),
        )
