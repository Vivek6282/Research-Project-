"""
Trackside — Driver threshold views.

Read-only history of the old per-driver limits. Limits are now set per corner on the map
(zone.threshold_g); creating a per-driver limit answers 410 Gone.
"""

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAdminOrCoach
from drivers.models import DriverZoneThreshold
from drivers.serializers import DriverZoneThresholdSerializer


# Per-driver limits are retired: the map is the only place that sets g-force limits
LIMITS_RETIRED_MESSAGE = (
    "Limits are set per corner on the map: Maps, then Edit corners. Per-driver limits are no longer used."
)


class ThresholdListCreateView(generics.ListCreateAPIView):
    """
    GET /api/drivers/thresholds/ — list the old per-driver limits (history only, scoped by role)
    POST /api/drivers/thresholds/ — retired: answers 410 Gone (set limits on the map instead)

    Old per-driver rows stay in the table as history and are ignored when limits are applied.
    """

    serializer_class = DriverZoneThresholdSerializer

    def get_permissions(self):
        """Admin/Coach reach the POST (to be told it is retired); anyone signed in can read the history."""
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

    def create(self, request, *args, **kwargs):
        """Creating a per-driver limit is retired: 410 Gone, nothing is stored."""
        return Response({"detail": LIMITS_RETIRED_MESSAGE}, status=status.HTTP_410_GONE)


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
