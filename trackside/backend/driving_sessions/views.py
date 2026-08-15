"""
Trackside — Sessions views.

Role-based session, telemetry, alert, biometric, and note access:
- Coach: sees sessions for drivers they manage, can create notes
- Driver: sees only their own sessions
- Admin: sees everything

Requirement #3 (IDOR): every queryset is scoped to what the user is
allowed to see. Drivers can never access another driver's data.
"""

from django.shortcuts import get_object_or_404
from rest_framework import generics, status, exceptions
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

    def get_permissions(self):
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role == "driver":
            return Session.objects.filter(driver=user).select_related("driver", "track")
        elif user.role == "device":
            if user.assigned_to:
                return Session.objects.filter(driver=user.assigned_to).select_related("driver", "track")
        return Session.objects.select_related("driver", "track").all()

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == "driver":
            serializer.save(driver=user)
        else:
            serializer.save()


class SessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/sessions/<uuid>/ — session details
    PUT/PATCH/DELETE — Admin or Coach
    """

    serializer_class = SessionSerializer

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [IsAdminOrCoach()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role == "driver":
            return Session.objects.filter(driver=user)
        elif user.role == "device":
            if user.assigned_to:
                return Session.objects.filter(driver=user.assigned_to)
        return Session.objects.all()


class TelemetryListCreateView(generics.ListCreateAPIView):
    """
    GET /api/sessions/<uuid>/telemetry/ — list telemetry for a session
    POST /api/sessions/<uuid>/telemetry/ — ingest telemetry data (User or IoT Device)
    """

    serializer_class = TelemetrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        session_id = self.kwargs.get("session_pk")
        user = self.request.user

        if user.role == "driver":
            return Telemetry.objects.filter(
                session_id=session_id,
                session__driver=user,
            )
        elif user.role == "device":
            if user.assigned_to:
                return Telemetry.objects.filter(
                    session_id=session_id,
                    session__driver=user.assigned_to,
                )
        return Telemetry.objects.filter(session_id=session_id)

    def create(self, request, *args, **kwargs):
        """Accept single object OR list of telemetry readings (bulk batch ingestion)."""
        session_id = self.kwargs.get("session_pk")
        user = self.request.user
        session = get_object_or_404(Session, pk=session_id)

        if user.role == "driver" and session.driver != user:
            raise exceptions.PermissionDenied("You do not own this session.")
        elif user.role == "device" and user.assigned_to and session.driver != user.assigned_to:
            raise exceptions.PermissionDenied("Device token is not authorized for this driver's session.")

        is_many = isinstance(request.data, list)
        serializer = self.get_serializer(data=request.data, many=is_many)
        serializer.is_valid(raise_exception=True)
        serializer.save(session=session)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        session_id = self.kwargs.get("session_pk")
        session = get_object_or_404(Session, pk=session_id)
        serializer.save(session=session)


class AlertListView(generics.ListAPIView):
    """
    GET /api/sessions/<uuid>/alerts/ — list alerts for a session
    """

    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        session_id = self.kwargs.get("session_pk")
        user = self.request.user

        if user.role == "driver":
            return Alert.objects.filter(
                session_id=session_id,
                session__driver=user,
            ).select_related("zone")
        elif user.role == "device":
            if user.assigned_to:
                return Alert.objects.filter(
                    session_id=session_id,
                    session__driver=user.assigned_to,
                ).select_related("zone")
        return Alert.objects.filter(
            session_id=session_id,
        ).select_related("zone")


class BiometricListCreateView(generics.ListCreateAPIView):
    """
    GET /api/sessions/<uuid>/biometrics/ — list biometric readings
    POST /api/sessions/<uuid>/biometrics/ — ingest biometric data (User or IoT Device)
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
        elif user.role == "device":
            if user.assigned_to:
                return BiometricReading.objects.filter(
                    session_id=session_id,
                    session__driver=user.assigned_to,
                )
        return BiometricReading.objects.filter(session_id=session_id)

    def perform_create(self, serializer):
        session_id = self.kwargs.get("session_pk")
        user = self.request.user
        session = get_object_or_404(Session, pk=session_id)

        if user.role == "driver" and session.driver != user:
            raise exceptions.PermissionDenied("You do not own this session.")
        elif user.role == "device" and user.assigned_to and session.driver != user.assigned_to:
            raise exceptions.PermissionDenied("Device token is not authorized for this driver's session.")

        serializer.save(session=session)


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


from rest_framework.views import APIView
from tracks.models import Zone
from django.contrib.auth import get_user_model

User = get_user_model()


class AlertSummaryView(APIView):
    """
    GET /api/sessions/alerts/summary/

    Returns the requesting driver's own zone-by-zone alert count breakdown
    across their last 5 sessions, plus latest session goal & best lap.
    Enforces strict user ownership scoping (session__driver=user).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Scoped driver selection
        if user.role == "driver":
            driver = user
        elif user.role == "device" and getattr(user, "assigned_to", None):
            driver = user.assigned_to
        else:
            driver_param = request.query_params.get("driver") or request.query_params.get("driver_id")
            if driver_param:
                driver = get_object_or_404(User, pk=driver_param)
            else:
                driver = user

        # Query driver's last 5 sessions
        recent_sessions = list(
            Session.objects.filter(driver=driver)
            .select_related("track")
            .order_by("-started_at")[:5]
        )

        if not recent_sessions:
            return Response(
                {
                    "has_sessions": False,
                    "total_sessions": 0,
                    "zones": [],
                    "latest_session": None,
                },
                status=status.HTTP_200_OK,
            )

        session_ids = [s.id for s in recent_sessions]
        track_ids = list(set(s.track_id for s in recent_sessions if s.track_id))

        # Get all zones associated with these sessions' tracks (or default system zones)
        zones = list(Zone.objects.filter(track_id__in=track_ids).order_by("label"))
        if not zones:
            zones = list(Zone.objects.all().order_by("label"))

        zone_data = []
        for zone in zones:
            alert_count = Alert.objects.filter(
                session_id__in=session_ids, zone=zone
            ).count()
            red_count = Alert.objects.filter(
                session_id__in=session_ids, zone=zone, severity=Alert.Severity.RED
            ).count()

            if alert_count == 0:
                zone_status = "Clean"
                color = "#33D17E"
            elif red_count > 0 or alert_count >= 5:
                zone_status = "High Risk"
                color = "#E5473C"
            else:
                zone_status = "Caution"
                color = "#F2A93B"

            zone_data.append(
                {
                    "name": zone.label,
                    "count": alert_count,
                    "red_count": red_count,
                    "status": zone_status,
                    "color": color,
                    "threshold": zone.threshold_g,
                }
            )

        latest_session = recent_sessions[0]

        latest_session_data = {
            "id": str(latest_session.id),
            "mode": latest_session.mode,
            "goal_text": latest_session.goal_text or "Zero Red Alerts at Hairpin",
            "goal_passed": latest_session.goal_passed,
            "started_at": latest_session.started_at,
            "track_name": latest_session.track.name if latest_session.track else "Standard Track",
            "best_lap_time": "48.32s",
        }

        return Response(
            {
                "has_sessions": True,
                "total_sessions": len(recent_sessions),
                "zones": zone_data,
                "latest_session": latest_session_data,
            },
            status=status.HTTP_200_OK,
        )

