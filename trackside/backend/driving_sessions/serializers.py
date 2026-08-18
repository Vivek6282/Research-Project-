"""
Trackside — Sessions serializers.

Handles serialization for sessions, telemetry, alerts, biometrics, and notes.
Requirement #3 (IDOR): serializers include validation but queryset scoping
happens in views — serializers validate data shape, views enforce access.
"""

from rest_framework import serializers
from driving_sessions.models import (
    Session, Telemetry, Alert, BiometricReading, SessionNote,
)


class SessionSerializer(serializers.ModelSerializer):
    """Read/write serializer for driving sessions with computed statistics."""

    driver_name = serializers.SerializerMethodField()
    track_name = serializers.SerializerMethodField()
    alert_count = serializers.SerializerMethodField()
    default_suggested_threshold = serializers.ReadOnlyField()
    duration = serializers.SerializerMethodField()
    kart = serializers.SerializerMethodField()
    laps = serializers.SerializerMethodField()
    best_lap = serializers.SerializerMethodField()
    max_g = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = [
            "id", "driver", "driver_name", "track", "track_name",
            "mode", "goal_text", "goal_passed", "kart_number",
            "started_at", "ended_at", "alert_count", "default_suggested_threshold",
            "duration", "kart", "laps", "best_lap", "max_g",
        ]
        read_only_fields = [
            "id", "driver_name", "track_name", "alert_count",
            "default_suggested_threshold", "duration", "kart",
            "laps", "best_lap", "max_g",
        ]

    def get_driver_name(self, obj):
        return obj.driver.name if obj.driver else None

    def get_track_name(self, obj):
        return obj.track.name if obj.track else None

    def get_alert_count(self, obj):
        return obj.alerts.count()

    def get_duration(self, obj):
        """Format session duration (e.g. '38 min') or 'In progress' if active."""
        if not obj.started_at:
            return None
        if not obj.ended_at:
            return "In progress"
        delta = obj.ended_at - obj.started_at
        minutes = int(delta.total_seconds() // 60)
        return f"{minutes} min"

    def get_kart(self, obj):
        """Format kart number (e.g. '#12')."""
        if obj.kart_number:
            val = str(obj.kart_number).strip()
            return val if val.startswith("#") else f"#{val}"
        return None

    def get_max_g(self, obj):
        """Compute MAX(lateral_g) across that session's Telemetry records."""
        from django.db.models import Max
        res = obj.telemetry_readings.aggregate(max_lateral=Max("lateral_g"))
        max_val = res.get("max_lateral")
        if max_val is not None:
            return f"{max_val:.2f}g"
        return None

    def get_laps(self, obj):
        """Compute MAX(lap_number) for the session if telemetry has lap tracking."""
        from django.db.models import Max
        res = obj.telemetry_readings.aggregate(max_lap=Max("lap_number"))
        return res.get("max_lap")

    def get_best_lap(self, obj):
        """Placeholder for best lap duration once lap boundary ingestion is active."""
        return None



class TelemetrySerializer(serializers.ModelSerializer):
    """Serializer for individual telemetry readings."""

    class Meta:
        model = Telemetry
        fields = [
            "id", "session", "zone", "recorded_at",
            "lateral_g", "speed_kmh", "gps_lat", "gps_lng",
        ]
        read_only_fields = ["id", "session"]


class AlertSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for alerts.
    Alerts are insert-only — they're created by the system,
    not directly by API users.
    """

    zone_label = serializers.SerializerMethodField()

    class Meta:
        model = Alert
        fields = [
            "id", "session", "zone", "zone_label", "severity",
            "g_value", "threshold_applied", "triggered_at",
        ]
        read_only_fields = ["id", "session", "zone_label"]

    def get_zone_label(self, obj):
        return obj.zone.label if obj.zone else None


class BiometricReadingSerializer(serializers.ModelSerializer):
    """Serializer for biometric readings."""

    class Meta:
        model = BiometricReading
        fields = [
            "id", "session", "recorded_at",
            "heart_rate", "spo2", "breathing_rate",
        ]
        read_only_fields = ["id", "session"]


class SessionNoteSerializer(serializers.ModelSerializer):
    """
    Serializer for coaching notes.
    coach is set automatically from the request — not user-supplied.
    """

    coach_name = serializers.SerializerMethodField()
    zone_label = serializers.SerializerMethodField()

    class Meta:
        model = SessionNote
        fields = [
            "id", "session", "coach", "coach_name",
            "zone", "zone_label", "note_text", "created_at",
        ]
        read_only_fields = ["id", "coach", "coach_name", "zone_label", "created_at"]

    def get_coach_name(self, obj):
        return obj.coach.name if obj.coach else None

    def get_zone_label(self, obj):
        return obj.zone.label if obj.zone else None
