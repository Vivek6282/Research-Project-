"""
Trackside — Devices views.

Device management is Admin-only. Other roles can view device status
for awareness but cannot modify device records.
"""

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsAdmin
from devices.models import Device, DeviceCommand
from devices.serializers import DeviceSerializer, DeviceCommandSerializer


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


class AdminDeviceCommandView(generics.ListCreateAPIView):
    """
    GET /api/devices/<id>/commands/ - Admin views command history.
    POST /api/devices/<id>/commands/ - Admin creates a pending command.
    """
    permission_classes = [IsAdmin]
    serializer_class = DeviceCommandSerializer

    def get_queryset(self):
        device_id = self.kwargs.get("pk")
        return DeviceCommand.objects.filter(device_id=device_id).order_by("-requested_at")

    def perform_create(self, serializer):
        device_id = self.kwargs.get("pk")
        device = generics.get_object_or_404(Device, pk=device_id)
        serializer.save(
            device=device,
            requested_by=self.request.user,
            status=DeviceCommand.Status.PENDING
        )


class DevicePendingCommandsView(generics.ListAPIView):
    """
    GET /api/devices/me/commands/pending/
    Device fetches its own pending commands. Authenticated via DeviceTokenAuthentication.
    """
    serializer_class = DeviceCommandSerializer

    def get_queryset(self):
        # request.user is a DeviceUser object
        device = self.request.user.device
        return DeviceCommand.objects.filter(
            device=device,
            status=DeviceCommand.Status.PENDING
        ).order_by("requested_at")


class DeviceCompleteCommandView(generics.UpdateAPIView):
    """
    POST (or PATCH) /api/devices/me/commands/<id>/complete/
    Device marks a command as completed or failed and submits results.
    """
    serializer_class = DeviceCommandSerializer
    http_method_names = ['post', 'patch']

    def get_queryset(self):
        device = self.request.user.device
        return DeviceCommand.objects.filter(device=device)

    def post(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        from django.utils import timezone
        instance = self.get_object()
        
        status = request.data.get("status", DeviceCommand.Status.COMPLETED)
        result = request.data.get("result", None)

        instance.status = status
        instance.result = result
        instance.completed_at = timezone.now()
        instance.save(update_fields=["status", "result", "completed_at"])

        serializer = self.get_serializer(instance)
        from rest_framework.response import Response
        return Response(serializer.data)
