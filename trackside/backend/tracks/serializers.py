"""
Trackside — Tracks serializers.

Handles serialization of Track and Zone data for API responses.
Zone data is nested inside Track responses for convenience.
"""

from rest_framework import serializers
from tracks.models import Track, Zone


class ZoneSerializer(serializers.ModelSerializer):
    """Serializer for Zone — includes track reference."""

    class Meta:
        model = Zone
        fields = ["id", "track", "label", "threshold_g", "gps_range"]
        read_only_fields = ["id"]


class TrackSerializer(serializers.ModelSerializer):
    """Serializer for Track — includes nested zones."""

    zones = ZoneSerializer(many=True, read_only=True)

    class Meta:
        model = Track
        fields = [
            "id", "name", "reference_line", "kart_class",
            "surveyed_at", "created_by", "zones",
        ]
        read_only_fields = ["id", "created_by"]
