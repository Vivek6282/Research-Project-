"""
Trackside — Devices views.

Device management is Admin-only. Other roles can view device status
for awareness but cannot modify device records.
"""

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsAdmin
from devices.models import Device
from devices.serializers import DeviceSerializer


class DeviceListCreateView(generics.ListCreateAPIView):
    """
    GET /api/devices/ — list all devices (any authenticated user)
    POST /api/devices/ — register a new device (Admin only)
    """

    serializer_class = DeviceSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return Device.objects.select_related("assigned_to").all()


class DeviceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/devices/<uuid>/ — device details
    PUT/PATCH/DELETE — Admin only
    """

    serializer_class = DeviceSerializer

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return Device.objects.select_related("assigned_to").all()
