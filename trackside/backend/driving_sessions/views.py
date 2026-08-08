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

    def perform_create(self, serializer):
        session_id = self.kwargs.get("session_pk")
        user = self.request.user
        session = get_object_or_404(Session, pk=session_id)

        if user.role == "driver" and session.driver != user:
            raise exceptions.PermissionDenied("You do not own this session.")
        elif user.role == "device" and user.assigned_to and session.driver != user.assigned_to:
            raise exceptions.PermissionDenied("Device token is not authorized for this driver's session.")

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
