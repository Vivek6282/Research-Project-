"""Trackside — Devices serializers."""

from rest_framework import serializers
from devices.models import Device


class DeviceSerializer(serializers.ModelSerializer):
    """
    Serializer for IoT devices.
    Returns raw_api_key ONCE on creation to the Admin, never on subsequent reads.
    """

    assigned_to_name = serializers.SerializerMethodField()
    raw_api_key = serializers.CharField(read_only=True, required=False)

    class Meta:
        model = Device
        fields = [
            "id", "device_type", "assigned_to", "assigned_to_name",
            "status", "last_seen_at", "raw_api_key",
        ]
        read_only_fields = ["id", "last_seen_at", "raw_api_key"]

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.name if obj.assigned_to else None

    def create(self, validated_data):
        instance = super().create(validated_data)
        raw_token = instance.set_api_key()
        instance.save(update_fields=["api_key_hash"])
        instance._raw_api_key = raw_token
        return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Only include raw_api_key once when created
        if hasattr(instance, "_raw_api_key"):
            ret["raw_api_key"] = instance._raw_api_key
        else:
            ret.pop("raw_api_key", None)
        return ret
