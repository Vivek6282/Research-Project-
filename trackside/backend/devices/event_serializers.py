"""Trackside — Serializer for device events (Phase 2.0)."""

from rest_framework import serializers

from devices.event_models import DeviceEvent
from devices.event_schemas import payload_errors

MAX_SEQUENCE = 2 ** 63 - 1


class DeviceEventSerializer(serializers.ModelSerializer):
    """Checks the envelope (id, type, times, counter) and the type's payload; the view checks who may send it."""

    session = serializers.UUIDField(required=False, allow_null=True, source="session_id")
    sequence = serializers.IntegerField(min_value=0, max_value=MAX_SEQUENCE)
    payload = serializers.JSONField(required=False, default=dict)

    class Meta:
        model = DeviceEvent
        fields = ["id", "event_id", "event_type", "session", "occurred_at", "sequence", "received_at", "payload"]
        read_only_fields = ["id", "received_at"]
        # Repeats of an event_id are answered by the view (idempotent), not refused as duplicates
        extra_kwargs = {"event_id": {"validators": []}}

    def validate(self, attrs):
        """Check the payload against the rules for its event type."""
        errors = payload_errors(attrs["event_type"], attrs.get("payload", {}))
        if errors:
            raise serializers.ValidationError({"payload": errors})
        return attrs
