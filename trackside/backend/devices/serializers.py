"""Trackside — Devices serializers."""

from rest_framework import serializers
from devices.models import Device


class DeviceSerializer(serializers.ModelSerializer):
    """Serializer for IoT devices."""

    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = [
            "id", "device_type", "assigned_to", "assigned_to_name",
            "status", "last_seen_at",
        ]
        read_only_fields = ["id"]

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.name if obj.assigned_to else None
