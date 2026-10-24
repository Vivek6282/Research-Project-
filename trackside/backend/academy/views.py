"""
Trackside — Academy settings and driver consent endpoints (Admin only).

GET/PATCH /api/academy/settings/                 retention period
GET/PATCH /api/academy/drivers/<uuid>/consent/   a driver's consent and under-18 flags
"""

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from accounts.models import AuditLogEntry
from accounts.permissions import IsAdmin
from academy.models import AcademySettings
from academy.serializers import AcademySettingsSerializer, DriverConsentSerializer

User = get_user_model()


class AcademySettingsView(GenericAPIView):
    """Read or change the academy-wide settings."""

    permission_classes = [IsAdmin]
    serializer_class = AcademySettingsSerializer

    def get(self, request):
        """The current settings."""
        return Response(self.get_serializer(AcademySettings.current()).data)

    def patch(self, request):
        """Change the retention period and write it to the audit log."""
        settings_row = AcademySettings.current()
        before = settings_row.retention_months
        serializer = self.get_serializer(settings_row, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        AuditLogEntry.objects.create(
            actor=request.user, action=AuditLogEntry.Action.SETTINGS_CHANGED, target_user_id="", target_user_name="",
            details=f"Data retention changed from {before} to {serializer.instance.retention_months} months")
        return Response(serializer.data)


class DriverConsentView(GenericAPIView):
    """Read or change one driver's consent and under-18 flags."""

    permission_classes = [IsAdmin]
    serializer_class = DriverConsentSerializer

    def get_driver(self, pk):
        """The driver with this id (404 for a missing user and for a coach or admin alike)."""
        return get_object_or_404(User, pk=pk, role="driver")

    def get(self, request, pk=None):
        """The driver's current flags."""
        return Response(self.get_serializer(self.get_driver(pk)).data)

    def patch(self, request, pk=None):
        """Record or withdraw consent, or set the under-18 flag, and log the change."""
        driver = self.get_driver(pk)
        serializer = self.get_serializer(driver, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        flags = serializer.data
        AuditLogEntry.objects.create(
            actor=request.user, action=AuditLogEntry.Action.CONSENT_CHANGED, target_user_id=str(driver.id),
            target_user_name=driver.name,
            details=f"Consent {'recorded' if flags['consent_recorded'] else 'not recorded'}; "
                    f"under 18: {'yes' if flags['is_under_18'] else 'no'}")
        return Response(flags)
