"""
Trackside — Tracks serializers.

Handles serialization of Track and Zone data for API responses.
Zone data is nested inside Track responses for convenience.
"""

from rest_framework import serializers
from tracks.demo_circuit import schematic_outline_json
from tracks.limit_history import set_zone_limit
from tracks.models import Track, Zone, ZoneThresholdHistory
from tracks.zone_rules import gps_range_problem, label_problem


class ZoneSerializer(serializers.ModelSerializer):
    """Serializer for Zone — includes track reference, corner_type, and min_threshold_g."""

    min_threshold_g = serializers.ReadOnlyField()

    class Meta:
        model = Zone
        fields = ["id", "track", "label", "corner_type", "threshold_g", "min_threshold_g", "gps_range", "is_active"]
        read_only_fields = ["id", "track", "min_threshold_g", "is_active"]

    def validate_label(self, value):
        """Name: required, at most 40 characters, not starting with 'Straight'."""
        problem = label_problem(value)
        if problem:
            raise serializers.ValidationError(problem)
        return value.strip()

    def validate_gps_range(self, value):
        """gps_range: start and end points inside the earth's range."""
        problem = gps_range_problem(value)
        if problem:
            raise serializers.ValidationError(problem)
        return value

    def validate(self, attrs):
        """A new zone needs a gps_range, and the limit must sit inside its track's allowed range."""
        if self.instance is None and not attrs.get("gps_range"):
            raise serializers.ValidationError({"gps_range": "gps_range is required when adding a corner."})
        track = self.context.get("track") or getattr(self.instance, "track", None)
        limit = attrs.get("threshold_g")
        if track is not None and limit is not None and not (track.min_threshold_g <= limit <= track.max_threshold_g):
            raise serializers.ValidationError(
                {"threshold_g": f"The limit must be from {track.min_threshold_g} to {track.max_threshold_g} g."}
            )
        return attrs

    def update(self, instance, validated_data):
        """Save the zone; a changed g limit goes through the insert-only history."""
        new_limit = validated_data.pop("threshold_g", None)
        request = self.context.get("request")
        instance = super().update(instance, validated_data)
        if new_limit is not None:
            set_zone_limit(instance, new_limit, getattr(request, "user", None))
        return instance


class ZoneThresholdHistorySerializer(serializers.ModelSerializer):
    """Read-only view of one zone limit change."""

    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ZoneThresholdHistory
        fields = ["id", "zone", "old_g", "new_g", "changed_by_name", "changed_at"]
        read_only_fields = fields

    def get_changed_by_name(self, obj):
        """Name of the user who changed the limit, or None if that user is gone."""
        return obj.changed_by.name if obj.changed_by else None


class TrackSerializer(serializers.ModelSerializer):
    """Serializer for Track — includes nested zones and min_threshold_g."""

    zones = serializers.SerializerMethodField()
    min_threshold_g = serializers.ReadOnlyField()
    schematic_outline = serializers.SerializerMethodField()
    is_schematic = serializers.SerializerMethodField()

    def get_schematic_outline(self, obj):
        """The built-in map's drawn-shape outline for thumbnails; None for every other map."""
        return schematic_outline_json() if obj.is_builtin and not obj.reference_line else None

    def get_is_schematic(self, obj):
        """True when the outline shown for this map is a schematic picture, not a GPS survey."""
        return bool(obj.is_builtin and not obj.reference_line)

    def get_zones(self, obj):
        """Active zones only; corners removed from a track keep their history but are hidden here."""
        return ZoneSerializer([z for z in obj.zones.all() if z.is_active], many=True, context=self.context).data

    class Meta:
        model = Track
        fields = [
            "id", "name", "reference_line", "kart_class", "min_threshold_g",
            "surveyed_at", "created_by", "zones", "is_builtin", "is_archived", "source",
            "schematic_outline", "is_schematic",
        ]
        read_only_fields = [
            "id", "created_by", "min_threshold_g", "is_builtin", "is_archived", "source",
            "schematic_outline", "is_schematic",
        ]

