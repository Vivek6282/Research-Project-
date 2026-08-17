"""
Trackside — Tracks app.

Manages karting tracks and their zones (corners/sections).
Zones are the fundamental unit for safety monitoring — each has a
calibrated g-force threshold that triggers alerts when exceeded.
"""

import uuid
from django.db import models
from django.conf import settings


class Track(models.Model):
    """
    A karting track layout with its reference racing line.

    Tracks are created by admins (or coaches with admin approval).
    Each track has multiple zones where g-force monitoring is active.
    """

    class KartClass(models.TextChoices):
        RENTAL = "rental", "Rental"
        SPRINT = "sprint", "Sprint"

    KART_CLASS_FLOOR = {
        KartClass.RENTAL: 0.4,
        KartClass.SPRINT: 1.0,
    }

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=150,
        help_text="Display name for the track (e.g. 'Kari Motor Speedway')",
    )

    reference_line = models.JSONField(
        null=True,
        blank=True,
        help_text="GPS coordinates of the ideal racing line (JSON array of lat/lng points)",
    )

    kart_class = models.CharField(
        max_length=10,
        choices=KartClass.choices,
        default=KartClass.RENTAL,
        help_text="Type of karts used on this track — affects threshold calibration",
    )

    surveyed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the track was last surveyed for zone boundaries",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_tracks",
        help_text="User who added this track to the system",
    )

    class Meta:
        db_table = "tracks"
        ordering = ["name"]

    @property
    def min_threshold_g(self) -> float:
        """Plausible g-force floor based on kart physics for this track's kart class."""
        return self.KART_CLASS_FLOOR.get(self.kart_class, 0.4)

    def __str__(self):
        return self.name


class Zone(models.Model):
    """
    A section of a track where g-force monitoring is active.

    Each zone has a calibrated threshold — the maximum safe lateral g-force.
    When a driver exceeds this threshold in a zone, an alert is triggered.
    Coaches can set per-driver thresholds that are lower than (never higher
    than) the zone's calibrated threshold.
    """

    class CornerType(models.TextChoices):
        HAIRPIN = "hairpin", "Hairpin"
        SWEEPER = "sweeper", "Sweeper"
        CHICANE = "chicane", "Chicane"
        STRAIGHT = "straight", "Straight"
        OTHER = "other", "Other"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    track = models.ForeignKey(
        Track,
        on_delete=models.CASCADE,
        related_name="zones",
        help_text="The track this zone belongs to",
    )

    label = models.CharField(
        max_length=100,
        help_text="Human-readable name (e.g. 'Hairpin', 'Sweeper', 'Chicane')",
    )

    corner_type = models.CharField(
        max_length=20,
        choices=CornerType.choices,
        default=CornerType.OTHER,
        blank=True,
        help_text="Fixed category classification for corner type",
    )

    threshold_g = models.FloatField(
        default=1.15,
        help_text="Calibrated safe g-force limit for this zone — driver thresholds cannot exceed this",
    )

    gps_range = models.JSONField(
        null=True,
        blank=True,
        help_text="GPS boundary for this zone (JSON with start/end coordinates)",
    )

    class Meta:
        db_table = "zones"
        ordering = ["track", "label"]

    @property
    def min_threshold_g(self) -> float:
        """Plausible g-force floor for this zone derived from its track's kart class."""
        if self.track:
            return self.track.min_threshold_g
        return 0.4

    def __str__(self):
        return f"{self.track.name} — {self.label}"


