"""
Trackside Driving Sessions — Biometric Ingestion and Query Views.
This module provides endpoints for driver biometric monitoring (heart rate, SpO2, breathing rate),
supporting ingestion from wearable IoT devices and live dashboard querying.
"""

from django.shortcuts import get_object_or_404
from rest_framework import generics, exceptions
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated

from academy.consent import require_consent
from devices.authentication import DeviceTokenAuthentication
from driving_sessions.access import sessions_visible_to, can_access_session
from driving_sessions.models import Session, BiometricReading
from driving_sessions.serializers import BiometricReadingSerializer


class BiometricListCreateView(generics.ListCreateAPIView):
    """
    GET /api/sessions/<uuid>/biometrics/ — list biometric measurements for an authorized session.
    POST /api/sessions/<uuid>/biometrics/ — ingest biometric data from wearable hardware or coach console.

    Security:
    - Ingestion accepts SessionAuthentication (coach/admin) or DeviceTokenAuthentication (wearable strap).
    - Checks can_access_session to verify driver/device ownership.
    """

    serializer_class = BiometricReadingSerializer
    authentication_classes = [SessionAuthentication, DeviceTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Returns biometric readings for the requested session if accessible to the user.
        Input: None.
        Output: Scoped BiometricReading QuerySet.
        """
        session_id = self.kwargs.get("session_pk")
        visible_sessions = sessions_visible_to(self.request.user)
        return BiometricReading.objects.filter(
            session_id=session_id,
            session__in=visible_sessions,
        )

    def create(self, request, *args, **kwargs):
        """Check who may use the session before the body is looked at, so outsiders cannot probe the rules."""
        target_session = get_object_or_404(Session, pk=self.kwargs.get("session_pk"))
        if not can_access_session(request.user, target_session):
            raise exceptions.PermissionDenied("You are not authorized for this driver's session.")
        # Phase 2.0: real biometric data needs the driver's recorded consent (demo runs are simulated)
        if not target_session.is_demo:
            require_consent(target_session.driver)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """
        Validates access rights before saving biometric readings linked to the session.
        Input: Validated BiometricReading serializer.
        Output: None.
        """
        session_id = self.kwargs.get("session_pk")
        requesting_user = self.request.user
        target_session = get_object_or_404(Session, pk=session_id)

        if not can_access_session(requesting_user, target_session):
            raise exceptions.PermissionDenied("You are not authorized for this driver's session.")

        serializer.save(session=target_session)
