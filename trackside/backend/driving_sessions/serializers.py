"""
Trackside — Sessions serializers.

Handles serialization for sessions, telemetry, alerts, biometrics, and notes.
Requirement #3 (IDOR): serializers include validation but queryset scoping
happens in views — serializers validate data shape, views enforce access.
"""

import math
from datetime import timedelta
from django.utils import timezone
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
            "duration", "kart", "laps", "best_lap", "max_g", "is_demo",
        ]
        read_only_fields = [
            "id", "driver_name", "track_name", "alert_count",
            "default_suggested_threshold", "duration", "kart",
            "laps", "best_lap", "max_g", "is_demo",
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
        """Shortest completed lap duration formatted as 'm:ss.mmm', or None."""
        return compute_best_lap(obj)


def compute_best_lap(session):
    """
    Compute the best (shortest) completed lap duration for a session.
    Lap time = max(recorded_at) - min(recorded_at) of telemetry sharing a lap_number.
    A lap is completed if a higher lap_number exists or the session has ended_at.
    Ignore laps with fewer than 5 readings.
    Format 'm:ss.mmm', or None if no qualifying lap exists.
    """
    from django.db.models import Min, Max, Count

    res = session.telemetry_readings.aggregate(max_lap=Max("lap_number"))
    max_lap = res.get("max_lap")
    if max_lap is None:
        return None

    session_ended = session.ended_at is not None

    lap_stats = (
        session.telemetry_readings.filter(lap_number__isnull=False)
        .values("lap_number")
        .annotate(
            min_time=Min("recorded_at"),
            max_time=Max("recorded_at"),
            readings_count=Count("id"),
        )
    )

    best_duration_ms = None

    for item in lap_stats:
        lap_num = item["lap_number"]
        count = item["readings_count"]
        if count < 5:
            continue

        is_completed = (lap_num < max_lap) or session_ended
        if not is_completed:
            continue

        min_time = item["min_time"]
        max_time = item["max_time"]
        if not min_time or not max_time:
            continue

        duration_ms = int(round((max_time - min_time).total_seconds() * 1000))
        if duration_ms < 0:
            continue

        if best_duration_ms is None or duration_ms < best_duration_ms:
            best_duration_ms = duration_ms

    if best_duration_ms is None:
        return None

    minutes = best_duration_ms // 60000
    rem_ms = best_duration_ms % 60000
    seconds = rem_ms // 1000
    millis = rem_ms % 1000
    return f"{minutes}:{seconds:02d}.{millis:03d}"



class TelemetrySerializer(serializers.ModelSerializer):
    """
    Serializer for individual telemetry readings with strict boundary validation (S4):
    - lateral_g: 0..10, reject NaN/inf
    - speed_kmh: 0..300, reject NaN/inf
    - gps_lat: -90..90, reject NaN/inf
    - gps_lng: -180..180, reject NaN/inf
    - lap_number: 1..999
    - recorded_at: not > 5 minutes in future
    """

    lap_number = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=999,
        allow_null=True,
        help_text="Lap number within the session (integer 1..999)",
    )

    class Meta:
        model = Telemetry
        fields = [
            "id", "session", "zone", "recorded_at",
            "lateral_g", "speed_kmh", "gps_lat", "gps_lng",
            "lap_number",
        ]
        read_only_fields = ["id", "session"]

    def validate_lateral_g(self, value):
        if value is None or not math.isfinite(value) or not (0.0 <= value <= 10.0):
            raise serializers.ValidationError("lateral_g must be a finite number between 0.0 and 10.0.")
        return value

    def validate_speed_kmh(self, value):
        if value is None or not math.isfinite(value) or not (0.0 <= value <= 300.0):
            raise serializers.ValidationError("speed_kmh must be a finite number between 0.0 and 300.0.")
        return value

    def validate_gps_lat(self, value):
        if value is not None:
            if not math.isfinite(value) or not (-90.0 <= value <= 90.0):
                raise serializers.ValidationError("gps_lat must be a finite number between -90.0 and 90.0.")
        return value

    def validate_gps_lng(self, value):
        if value is not None:
            if not math.isfinite(value) or not (-180.0 <= value <= 180.0):
                raise serializers.ValidationError("gps_lng must be a finite number between -180.0 and 180.0.")
        return value

    def validate_lap_number(self, value):
        if value is not None and not (1 <= value <= 999):
            raise serializers.ValidationError("lap_number must be between 1 and 999.")
        return value

    def validate_recorded_at(self, value):
        if value > timezone.now() + timedelta(minutes=5):
            raise serializers.ValidationError("recorded_at cannot be more than 5 minutes in the future.")
        return value


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
        read_only_fields = ["id", "session", "coach", "coach_name", "zone_label", "created_at"]

    def get_coach_name(self, obj):
        return obj.coach.name if obj.coach else None

    def get_zone_label(self, obj):
        return obj.zone.label if obj.zone else None
