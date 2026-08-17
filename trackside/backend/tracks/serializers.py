"""
Trackside — Tracks serializers.

Handles serialization of Track and Zone data for API responses.
Zone data is nested inside Track responses for convenience.
"""

from rest_framework import serializers
from tracks.models import Track, Zone


class ZoneSerializer(serializers.ModelSerializer):
    """Serializer for Zone — includes track reference, corner_type, and min_threshold_g."""

    min_threshold_g = serializers.ReadOnlyField()

    class Meta:
        model = Zone
        fields = ["id", "track", "label", "corner_type", "threshold_g", "min_threshold_g", "gps_range"]
        read_only_fields = ["id", "track", "min_threshold_g"]


class TrackSerializer(serializers.ModelSerializer):
    """Serializer for Track — includes nested zones and min_threshold_g."""

    zones = ZoneSerializer(many=True, read_only=True)
    min_threshold_g = serializers.ReadOnlyField()

    class Meta:
        model = Track
        fields = [
            "id", "name", "reference_line", "kart_class", "min_threshold_g",
            "surveyed_at", "created_by", "zones",
        ]
        read_only_fields = ["id", "created_by", "min_threshold_g"]

