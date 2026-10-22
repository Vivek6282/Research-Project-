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
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AuditLogEntry
from accounts.permissions import IsAdmin
from accounts.user_delete import blocked_reason, confirm_text_for, delete_counts
from accounts.serializers import (
    AuditLogEntrySerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from devices.models import Device

User = get_user_model()


def describe_profile(user) -> dict:
    """The profile values an edit can change, for the audit trail."""
    return {"name": user.name, "email": user.email, "role": user.role, "driver_code": user.driver_code}


def changes_text(before: dict, after: dict) -> str:
    """' (name: 'A' -> 'B'; driver_code: 'D1' -> 'D2')' for every value that changed, or '' when none did."""
    changed = [f"{key}: {before[key]!r} -> {after[key]!r}" for key in before if before[key] != after[key]]
    return f" ({'; '.join(changed)})" if changed else ""


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
    DELETE removes the user for good, only with the typed confirmation and the safeguards below.

    Security:
    - Scoped strictly to Admin users.
    - Tracks deactivation and reactivation in the audit log.
    - DELETE is refused for yourself, for Admin accounts and for a driver who is live right now (409);
      the body must carry {"confirm": "<driver code, or username for a coach>"} (400 otherwise).
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
        before = describe_profile(serializer.instance)
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
            audit_details = f"Updated profile information for {updated_user.name}{changes_text(before, describe_profile(updated_user))}"

        AuditLogEntry.objects.create(
            actor=acting_user,
            action=audit_action,
            target_user_id=str(updated_user.id),
            target_user_name=updated_user.name,
            details=audit_details,
        )


    def delete(self, request, pk=None):
        """Permanently delete the user: safeguards first, then the audit entry, then the delete (all or nothing)."""
        target = get_object_or_404(User, pk=pk)
        reason = blocked_reason(target, request.user)
        if reason:
            return Response({"detail": reason, "blocked_reason": reason}, status=status.HTTP_409_CONFLICT)
        confirm = request.data.get("confirm") if isinstance(request.data, dict) else None
        expected = confirm_text_for(target)
        if not expected or confirm != expected:
            return Response({"detail": f"Type {expected or 'the username'} exactly to confirm. Nothing was deleted."},
                            status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            counts = delete_counts(target)
            AuditLogEntry.objects.create(
                actor=request.user,
                action=AuditLogEntry.Action.DELETE_USER,
                target_user_id=str(target.id),
                target_user_name=target.name,
                details=f"Permanently deleted {target.role} {target.name} ({target.driver_code or target.username}); removed: {counts}",
            )
            target.delete()
        return Response({"deleted": True, "counts": counts}, status=status.HTTP_200_OK)


class UserDeletePreviewView(APIView):
    """GET /api/auth/users/<uuid:pk>/delete-preview/ — what a delete would remove. Changes nothing (Admin only)."""

    permission_classes = [IsAdmin]

    def get(self, request, pk=None):
        """Who the user is, whether the delete is allowed, why not, and the counts that would be removed."""
        target = get_object_or_404(User, pk=pk)
        reason = blocked_reason(target, request.user)
        return Response({
            "id": str(target.id), "name": target.name, "role": target.role, "username": target.username,
            "driver_code": target.driver_code, "can_delete": reason is None, "blocked_reason": reason,
            "counts": delete_counts(target),
        })


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
