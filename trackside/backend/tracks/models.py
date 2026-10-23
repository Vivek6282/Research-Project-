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

    class Source(models.TextChoices):
        MANUAL = "manual", "Added by hand"
        BUILTIN = "builtin", "Built-in"
        RACECHRONO_CSV = "racechrono_csv", "RaceChrono CSV"
        VBO = "vbo", "Racelogic VBO"
        DRAWN = "drawn", "Drawn on the map"

    # Corner limits the coach may set: sprint karts 0.3g-1.5g, rental karts 0.3g-0.8g.
    # A slow corner can have a limit well below 1 g, so the floor is the same for both classes.
    KART_CLASS_FLOOR = {
        KartClass.RENTAL: 0.3,
        KartClass.SPRINT: 0.3,
    }

    KART_CLASS_CEILING = {
        KartClass.RENTAL: 0.8,
        KartClass.SPRINT: 1.5,
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

    is_builtin = models.BooleanField(
        default=False,
        help_text="Built-in tracks (the Demo Circuit) are locked: no edit, archive or delete",
    )

    is_archived = models.BooleanField(
        default=False,
        help_text="Archived tracks are hidden from pickers but keep their session history",
    )

    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.MANUAL,
        help_text="Where the track shape came from",
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

    @property
    def max_threshold_g(self) -> float:
        """Plausible g-force ceiling based on kart physics for this track's kart class."""
        return self.KART_CLASS_CEILING.get(self.kart_class, 1.5)

    def __str__(self):
        return self.name


# Note on IMU Hardware Sensor Configuration:
# Sensor hardware (IMU) should be configured/verified to measure up to at least 2.5g without clipping,
# even though alert thresholds never exceed 1.5g — this protects against missing or misreading a genuine
# hard hit or curb strike, distinct from the alerting logic itself.


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
        default=1.50,
        help_text="Calibrated safe g-force limit for this zone — driver thresholds cannot exceed this",
    )

    gps_range = models.JSONField(
        null=True,
        blank=True,
        help_text="GPS boundary for this zone (JSON with start/end coordinates)",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="False once a corner with history is removed: hidden from new sessions, history kept",
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

    @property
    def max_threshold_g(self) -> float:
        """Plausible g-force ceiling for this zone derived from its track's kart class."""
        if self.track:
            return self.track.max_threshold_g
        return 1.5

    def __str__(self):
        return f"{self.track.name} — {self.label}"


class ZoneThresholdHistoryQuerySet(models.QuerySet):
    """Blocks bulk updates and deletes so the history can only grow."""

    def update(self, **kwargs):
        """Refuse bulk updates: history rows are never changed."""
        raise ValueError("Zone limit history is insert-only.")

    def delete(self):
        """Refuse bulk deletes: history rows are never removed."""
        raise ValueError("Zone limit history is insert-only.")


class ZoneThresholdHistory(models.Model):
    """
    One row each time a zone's calibrated g limit changes (insert-only).

    The newest row for a zone shows the latest change; the zone itself holds the
    current limit. Rows are removed only when their zone is deleted.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name="limit_history")
    old_g = models.FloatField(help_text="The limit before the change")
    new_g = models.FloatField(help_text="The limit after the change")
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="zone_limit_changes",
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    objects = ZoneThresholdHistoryQuerySet.as_manager()

    class Meta:
        db_table = "zone_threshold_history"
        ordering = ["-changed_at"]

    def save(self, *args, **kwargs):
        """Allow inserts only; an existing row can never be rewritten."""
        if not self._state.adding:
            raise ValueError("Zone limit history is insert-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Refuse single-row deletes."""
        raise ValueError("Zone limit history is insert-only.")

    def __str__(self):
        """Show the zone id and the change, e.g. "<id>: 1.3 -> 1.1"."""
        return f"{self.zone_id}: {self.old_g} -> {self.new_g}"
