"""
Trackside — Driver threshold serializers.

Handles validation that custom thresholds never exceed the zone's
calibrated safe limit. Insert-only pattern — no update endpoint.
"""

from rest_framework import serializers
from django.db import transaction

from drivers.models import DriverZoneThreshold
from tracks.models import Zone


class DriverZoneThresholdSerializer(serializers.ModelSerializer):
    """
    Serializer for driver-specific zone thresholds.

    Validates that custom_threshold_g ≤ zone.threshold_g.
    Coach who sets the threshold is recorded automatically.
    """

    driver_name = serializers.SerializerMethodField()
    zone_label = serializers.SerializerMethodField()
    set_by_name = serializers.SerializerMethodField()

    class Meta:
        model = DriverZoneThreshold
        fields = [
            "id", "driver", "driver_name", "zone", "zone_label",
            "custom_threshold_g", "set_by", "set_by_name", "updated_at",
        ]
        read_only_fields = ["id", "set_by", "set_by_name", "updated_at"]

    def get_driver_name(self, obj):
        return obj.driver.name if obj.driver else None

    def get_zone_label(self, obj):
        return obj.zone.label if obj.zone else None

    def get_set_by_name(self, obj):
        return obj.set_by.name if obj.set_by else None

    def validate(self, attrs):

        """
        Validate that the custom threshold:
        1. Does not exceed the zone's calibrated limit (upper bound)
        2. Is not below the track's kart_class floor (lower bound)
        Uses select_for_update() inside a transaction lock.
        """
        zone = attrs.get("zone")
        custom_threshold = attrs.get("custom_threshold_g")

        if zone and custom_threshold is not None:
            # Read the zone threshold inside a transaction lock
            with transaction.atomic():
                locked_zone = Zone.objects.select_for_update().get(pk=zone.pk)
                if custom_threshold > locked_zone.threshold_g:
                    raise serializers.ValidationError(
                        f"Custom threshold ({custom_threshold}g) cannot exceed "
                        f"the zone's calibrated limit ({locked_zone.threshold_g}g)."
                    )

                floor_g = locked_zone.min_threshold_g
                if custom_threshold < floor_g:
                    kart_class_label = locked_zone.track.kart_class if (locked_zone.track and locked_zone.track.kart_class) else "sprint"
                    raise serializers.ValidationError(
                        f"Custom threshold ({custom_threshold}g) is below the plausible floor "
                        f"({floor_g}g) for {kart_class_label}-class karts."
                    )

        return attrs

