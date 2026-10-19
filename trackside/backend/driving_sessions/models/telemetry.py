"""
Trackside Driving Sessions — Telemetry Reading Model.
This module defines the high-frequency Telemetry model capturing IMU lateral-g, GPS speed,
coordinates, and lap number for each sensor packet during a driving session.
"""

import uuid
from django.db import models
from driving_sessions.models.session import Session


class Telemetry(models.Model):
    """
    A single telemetry measurement from a kart sensor node during an active driving session.
    Optimized with composite indexing on session and recorded_at for high-throughput queries.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="telemetry_readings",
        help_text="The session this reading belongs to",
    )

    zone = models.ForeignKey(
        "tracks.Zone",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="telemetry_readings",
        help_text="The zone where this reading was taken (null if on a straight)",
    )

    recorded_at = models.DateTimeField(
        help_text="Timestamp of this sensor reading",
    )

    lateral_g = models.FloatField(
        help_text="Lateral g-force measured by the IMU",
    )

    speed_kmh = models.FloatField(
        help_text="Speed in km/h from the GPS module",
    )

    gps_lat = models.FloatField(
        help_text="GPS latitude",
    )

    gps_lng = models.FloatField(
        help_text="GPS longitude",
    )

    lap_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Lap number within the session",
    )

    class Meta:
        app_label = "driving_sessions"
        db_table = "telemetry"
        ordering = ["session", "recorded_at"]
        indexes = [
            models.Index(
                fields=["session", "recorded_at"],
                name="idx_telemetry_session_time",
            ),
        ]

    def __str__(self):
        return f"Telemetry {self.session_id} @ {self.recorded_at}"
