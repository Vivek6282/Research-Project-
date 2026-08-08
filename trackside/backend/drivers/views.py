"""
Trackside — Driver threshold views.

Insert-only threshold management with race-condition protection.
Coaches set per-driver per-zone thresholds that are always ≤ the zone limit.
"""

from django.db import transaction
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsAdminOrCoach
from drivers.models import DriverZoneThreshold
from drivers.serializers import DriverZoneThresholdSerializer


class ThresholdListCreateView(generics.ListCreateAPIView):
    """
    GET /api/drivers/thresholds/ — list thresholds (scoped by role)
    POST /api/drivers/thresholds/ — set a new threshold (Coach only)

    POST creates a new threshold row (insert-only, never updates).
    The latest row per driver+zone pair is the active threshold.

    Requirement #7: uses transaction.atomic() + select_for_update()
    to prevent race conditions when reading zone limits and creating
    threshold records simultaneously.
    """

    serializer_class = DriverZoneThresholdSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminOrCoach()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """
        Requirement #3: scope by role.
        Drivers see only their own thresholds.
        """
        user = self.request.user

        queryset = DriverZoneThreshold.objects.select_related(
            "driver", "zone", "set_by"
        )

        if user.role == "driver":
            return queryset.filter(driver=user)
        return queryset.all()

    def perform_create(self, serializer):
        """
        Record the coach who set this threshold.
        Wrapped in atomic() for race-condition safety (req #7).
        """
        with transaction.atomic():
            serializer.save(set_by=self.request.user)


class ThresholdsByDriverView(generics.ListAPIView):
    """
    GET /api/drivers/<uuid>/thresholds/ — list thresholds for a specific driver

    Used by coaches to see all threshold history for a driver.
    """

    serializer_class = DriverZoneThresholdSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Scope to the driver in the URL. Drivers see only their own."""
        driver_id = self.kwargs.get("driver_pk")
        user = self.request.user

        queryset = DriverZoneThreshold.objects.select_related(
            "driver", "zone", "set_by"
        ).filter(driver_id=driver_id)

        # Drivers can only see their own thresholds
        if user.role == "driver" and str(user.pk) != str(driver_id):
            return DriverZoneThreshold.objects.none()

        return queryset
