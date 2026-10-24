"""
Trackside — Devices views.

Device management is Admin-only. Coaches can view device status; drivers
cannot see devices at all (the data names other drivers). Only Admin can modify.
"""

import json

from rest_framework import generics
from rest_framework.authentication import SessionAuthentication
from devices.authentication import DeviceTokenAuthentication

from accounts.permissions import IsAdmin, IsAdminOrCoach, IsDevice
from devices.models import Device, DeviceCommand
from devices.serializers import DeviceSerializer, DeviceCommandSerializer


class DeviceListCreateView(generics.ListCreateAPIView):
    """
    GET /api/devices/ — list all devices (Admin and Coach; drivers get 403)
    POST /api/devices/ — register a new device (Admin only)
    """

    serializer_class = DeviceSerializer

    def get_permissions(self):
        """Admin registers devices; Admin and Coach read them."""
        if self.request.method == "POST":
            return [IsAdmin()]
        return [IsAdminOrCoach()]

    def get_queryset(self):
        return Device.objects.select_related("assigned_to").all()


class DeviceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/devices/<uuid>/ — device details (Admin and Coach; drivers get 403)
    PUT/PATCH/DELETE — Admin only
    """

    serializer_class = DeviceSerializer

    def get_permissions(self):
        """Admin changes a device; Admin and Coach read it."""
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [IsAdmin()]
        return [IsAdminOrCoach()]

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
    authentication_classes = [SessionAuthentication, DeviceTokenAuthentication]
    permission_classes = [IsDevice]
    serializer_class = DeviceCommandSerializer

    def get_queryset(self):
        """Pending commands of the calling device only."""
        # request.user is a DeviceUser object
        device = self.request.user.device
        return DeviceCommand.objects.filter(
            device=device,
            status=DeviceCommand.Status.PENDING
        ).order_by("requested_at")


# A self-test result is a short report; anything larger is refused
MAX_RESULT_BYTES = 4096


class DeviceCompleteCommandView(generics.UpdateAPIView):
    """
    POST (or PATCH) /api/devices/me/commands/<id>/complete/
    Device marks a command as completed or failed and submits results.
    """
    authentication_classes = [SessionAuthentication, DeviceTokenAuthentication]
    permission_classes = [IsDevice]
    serializer_class = DeviceCommandSerializer
    http_method_names = ['post', 'patch']

    def get_queryset(self):
        """Commands of the calling device only."""
        device = self.request.user.device
        return DeviceCommand.objects.filter(device=device)

    def post(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        from django.utils import timezone
        instance = self.get_object()
        
        status = request.data.get("status", DeviceCommand.Status.COMPLETED)
        if status not in (DeviceCommand.Status.COMPLETED, DeviceCommand.Status.FAILED):
            from rest_framework.response import Response
            return Response({"status": "Use 'completed' or 'failed'."}, status=400)
        if instance.status != DeviceCommand.Status.PENDING:
            from rest_framework.response import Response
            return Response({"detail": "This command is already finished."}, status=409)
        result = request.data.get("result", None)
        if result is not None and (not isinstance(result, dict) or len(json.dumps(result)) > MAX_RESULT_BYTES):
            from rest_framework.response import Response
            return Response({"result": f"Send an object of at most {MAX_RESULT_BYTES} bytes, or nothing."}, status=400)

        instance.status = status
        instance.result = result
        instance.completed_at = timezone.now()
        instance.save(update_fields=["status", "result", "completed_at"])

        serializer = self.get_serializer(instance)
        from rest_framework.response import Response
        return Response(serializer.data)
