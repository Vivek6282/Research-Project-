"""
Trackside Accounts — User Management & Administrative Views.
This module handles administrative user management, auditing, and system diagnostics:
listing and creating users, viewing/updating user profiles, security audit trails, and live diagnostics.
All endpoints require administrator privileges (IsAdmin).
"""

import time
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AuditLogEntry
from accounts.permissions import IsAdmin
from accounts.serializers import (
    AuditLogEntrySerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from devices.models import Device

User = get_user_model()


class UserListCreateView(generics.ListCreateAPIView):
    """
    GET /api/auth/users/ — list all user accounts (Admin only).
    POST /api/auth/users/ — provision a new Coach or Driver user (Admin only).

    Security:
    - Enforces IsAdmin permission check server-side.
    - Prevents arbitrary privilege escalation.
    - Records an immutable audit log entry upon user creation.
    """

    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        """
        Determines the appropriate serializer based on HTTP method.
        Input: Request method.
        Output: UserCreateSerializer for creation (POST), UserSerializer for reading (GET).
        """
        if self.request.method == "POST":
            return UserCreateSerializer
        return UserSerializer

    def get_queryset(self):
        """
        Returns all user accounts, optionally filtered by role query parameter.
        Input: Query parameter ?role=admin|coach|driver.
        Output: Filtered User QuerySet.
        """
        user_queryset = User.objects.all()

        role_filter = self.request.query_params.get("role")
        if role_filter and role_filter in ["admin", "coach", "driver"]:
            user_queryset = user_queryset.filter(role=role_filter)

        return user_queryset

    def perform_create(self, serializer):
        """
        Persists the newly created user and appends a security audit entry.
        Input: Validated user serializer.
        Output: None.
        """
        created_user = serializer.save()
        acting_user = self.request.user if self.request.user and self.request.user.is_authenticated else None
        AuditLogEntry.objects.create(
            actor=acting_user,
            action=AuditLogEntry.Action.CREATE_USER,
            target_user_id=str(created_user.id),
            target_user_name=created_user.name,
            details=f"Created {created_user.role.upper()} user {created_user.name} ({created_user.email or created_user.username})",
        )


class UserDetailView(generics.RetrieveUpdateAPIView):
    """
    GET /api/auth/users/<uuid:pk>/ — view detailed user record (Admin only).
    PUT/PATCH /api/auth/users/<uuid:pk>/ — update user details (Admin only).
    DELETE is deliberately disabled to preserve data integrity across racing sessions.

    Security:
    - Scoped strictly to Admin users.
    - Tracks deactivation and reactivation in the audit log.
    """

    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        """
        Selects serializer for update vs read operations.
        Input: Request method.
        Output: UserUpdateSerializer for PUT/PATCH, UserSerializer for GET.
        """
        if self.request.method in ("PUT", "PATCH"):
            return UserUpdateSerializer
        return UserSerializer

    def get_queryset(self):
        """
        Provides user records scoped by admin permission.
        Input: None.
        Output: Full User QuerySet.
        """
        return User.objects.all()

    def perform_update(self, serializer):
        """
        Saves user modifications and logs an audit trail event for activation changes or profile updates.
        Input: Validated user serializer with instance updates.
        Output: None.
        """
        was_previously_active = serializer.instance.is_active
        updated_user = serializer.save()
        acting_user = self.request.user if self.request.user and self.request.user.is_authenticated else None

        if was_previously_active != updated_user.is_active:
            if not updated_user.is_active:
                audit_action = AuditLogEntry.Action.DEACTIVATE_USER
                audit_details = f"Deactivated account for {updated_user.name}"
            else:
                audit_action = AuditLogEntry.Action.REACTIVATE_USER
                audit_details = f"Reactivated account for {updated_user.name}"
        else:
            audit_action = AuditLogEntry.Action.UPDATE_USER
            audit_details = f"Updated profile information for {updated_user.name}"

        AuditLogEntry.objects.create(
            actor=acting_user,
            action=audit_action,
            target_user_id=str(updated_user.id),
            target_user_name=updated_user.name,
            details=audit_details,
        )


class AuditLogListView(APIView):
    """
    GET /api/auth/audit-logs/

    Returns recent security audit logs and aggregate counts. Accessible by Admins only.
    """

    permission_classes = [IsAdmin]

    def get(self, request):
        """
        Calculates aggregate modification metrics and retrieves the 20 most recent audit entries.
        Input: Authenticated admin GET request.
        Output: JSON with count_30_days, total_count, and serialized log results.
        """
        thirty_days_cutoff = timezone.now() - timedelta(days=30)
        recent_log_count = AuditLogEntry.objects.filter(timestamp__gte=thirty_days_cutoff).count()
        total_log_count = AuditLogEntry.objects.count()
        recent_log_entries = AuditLogEntry.objects.select_related("actor").all()[:20]

        return Response(
            {
                "count_30_days": recent_log_count,
                "total_count": total_log_count,
                "results": AuditLogEntrySerializer(recent_log_entries, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminDiagnosticsView(APIView):
    """
    GET /api/auth/diagnostics/

    Provides live operational telemetry diagnostics and database response time benchmarks.
    Accessible by Admins only.
    """

    permission_classes = [IsAdmin]

    def get(self, request):
        """
        Measures real-time query latency and tallies active hardware telemetry nodes.
        Input: Authenticated admin GET request.
        Output: JSON telemetry diagnostic metrics.
        """
        start_benchmark_time = time.perf_counter()

        total_user_count = User.objects.count()
        total_hardware_nodes = Device.objects.count()
        window_sec = getattr(settings, "DEVICE_ONLINE_WINDOW_SECONDS", 30)
        online_cutoff = timezone.now() - timedelta(seconds=window_sec)
        active_hardware_nodes = Device.objects.filter(last_seen_at__gte=online_cutoff).count()
        thirty_days_cutoff = timezone.now() - timedelta(days=30)
        recent_audit_count = AuditLogEntry.objects.filter(timestamp__gte=thirty_days_cutoff).count()

        benchmark_duration_ms = (time.perf_counter() - start_benchmark_time) * 1000.0
        measured_database_latency_ms = round(max(benchmark_duration_ms, 0.45), 2)

        return Response(
            {
                "active_nodes": active_hardware_nodes,
                "total_nodes": total_hardware_nodes,
                "user_count": total_user_count,
                "db_query_time_ms": measured_database_latency_ms,
                "audit_count_30_days": recent_audit_count,
            },
            status=status.HTTP_200_OK,
        )
