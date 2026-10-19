"""
Trackside Driving Sessions — Telemetry Ingestion and Query Views.
This module handles high-frequency telemetry readings from kart IoT sensors and dashboards,
including batch boundary enforcement, range validation, concurrency locking, and alerting.
"""

from django.db import transaction
from rest_framework import generics, status, exceptions
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from devices.authentication import DeviceTokenAuthentication
from driving_sessions.access import sessions_visible_to, can_access_session
from driving_sessions.alerting import process_telemetry_alerts
from driving_sessions.models import Session, Telemetry
from driving_sessions.serializers import TelemetrySerializer


class DeviceTelemetryRateThrottle(ScopedRateThrottle):
    """
    Rate throttle for device telemetry ingestion.
    Resolves throttle limits dynamically from settings (default: 600 requests per minute).
    """

    scope = "device_telemetry"

    def get_rate(self):
        """
        Retrieves the rate configured for device_telemetry scope from Django settings.
        Input: None.
        Output: Rate string e.g. '600/min'.
        """
        from rest_framework.settings import api_settings
        configured_rates = getattr(api_settings, "DEFAULT_THROTTLE_RATES", {}) or {}
        return configured_rates.get(self.scope, self.THROTTLE_RATES.get(self.scope))


class TelemetryListCreateView(generics.ListCreateAPIView):
    """
    GET /api/sessions/<uuid>/telemetry/ — list telemetry readings for an authorized session.
    POST /api/sessions/<uuid>/telemetry/ — ingest single or batch telemetry points from devices or users.

    Security & Reliability Rules:
    - S1: Enforces can_access_session to deny access to other drivers' sessions.
    - S3: Authenticated via SessionAuthentication or DeviceTokenAuthentication.
    - S4: Rejects batches over 100 points, validates numerical ranges, rejects ended sessions.
    - S5: Locks the session row with select_for_update() inside transaction.atomic to prevent alert race conditions.
    """

    serializer_class = TelemetrySerializer
    authentication_classes = [SessionAuthentication, DeviceTokenAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [DeviceTelemetryRateThrottle]
    throttle_scope = "device_telemetry"

    def get_queryset(self):
        """
        Retrieves telemetry records scoped strictly to authorized sessions.
        Input: None.
        Output: Telemetry QuerySet matching session UUID and user visibility.
        """
        session_id = self.kwargs.get("session_pk")
        visible_sessions = sessions_visible_to(self.request.user)
        return Telemetry.objects.filter(
            session_id=session_id,
            session__in=visible_sessions,
        )

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Accepts a single telemetry reading or list of up to 100 readings.
        Locks the session row to prevent race conditions during alert processing.
        Input: JSON object or list of telemetry readings.
        Output: HTTP 201 with saved readings, or HTTP 400/403/404/409 on validation failure.
        """
        session_id = self.kwargs.get("session_pk")
        requesting_user = self.request.user

        is_batch_submission = isinstance(request.data, list)
        if is_batch_submission and len(request.data) > 100:
            return Response(
                {"error": "Batch size cannot exceed 100 readings."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Concurrency / Race Condition Protection (S5):
        # Lock the Session row using select_for_update() within transaction.atomic
        # to serialize concurrent telemetry batches for the same session, preventing
        # race conditions where process_telemetry_alerts could double-create or mis-order alerts.
        # Note: SQLite ignores row locks; fully effective on PostgreSQL in production.
        try:
            target_session = Session.objects.select_for_update().get(pk=session_id)
        except Session.DoesNotExist:
            raise exceptions.NotFound("Session not found.")

        # S1: Access scoping via centralized access helper
        if not can_access_session(requesting_user, target_session):
            raise exceptions.PermissionDenied("You are not authorized for this driver's session.")

        # S4: Reject posting to a session that has ended_at set (409)
        if target_session.ended_at is not None:
            return Response(
                {"error": "Cannot post telemetry to an ended session."},
                status=status.HTTP_409_CONFLICT,
            )

        telemetry_serializer = self.get_serializer(data=request.data, many=is_batch_submission)
        telemetry_serializer.is_valid(raise_exception=True)
        persisted_instances = telemetry_serializer.save(session=target_session)
        if not is_batch_submission:
            persisted_instances = [persisted_instances]

        process_telemetry_alerts(target_session, persisted_instances)

        response_headers = self.get_success_headers(telemetry_serializer.data)
        return Response(telemetry_serializer.data, status=status.HTTP_201_CREATED, headers=response_headers)

    @transaction.atomic
    def perform_create(self, serializer):
        """
        Fallback perform_create implementing single-item authorization and locking.
        Input: Validated Telemetry serializer.
        Output: None.
        """
        session_id = self.kwargs.get("session_pk")
        target_session = Session.objects.select_for_update().get(pk=session_id)
        if not can_access_session(self.request.user, target_session):
            raise exceptions.PermissionDenied("You are not authorized for this driver's session.")
        if target_session.ended_at is not None:
            raise exceptions.PermissionDenied("Cannot post telemetry to an ended session.")
        created_instance = serializer.save(session=target_session)
        process_telemetry_alerts(target_session, [created_instance])
