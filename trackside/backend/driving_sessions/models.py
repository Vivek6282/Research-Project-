"""
Trackside — Sessions app models.

Covers live and historical session data: sessions, telemetry readings,
alerts, biometric readings, and coach session notes.
"""

import uuid
from django.db import models
from django.conf import settings


class Session(models.Model):
    """
    A driving session — the period from when a driver starts on track
    to when they finish. Each session has a mode (safety/performance)
    and an optional coaching goal.
    """

    class Mode(models.TextChoices):
        SAFETY = "safety", "Safety"
        PERFORMANCE = "performance", "Performance"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sessions",
        help_text="The driver for this session",
    )

    track = models.ForeignKey(
        "tracks.Track",
        on_delete=models.CASCADE,
        related_name="sessions",
        help_text="The track where this session took place",
    )

    mode = models.CharField(
        max_length=15,
        choices=Mode.choices,
        default=Mode.SAFETY,
        help_text="Session mode — determines alert thresholds and coaching focus",
    )

    goal_text = models.TextField(
        blank=True,
        default="",
        help_text="Free-text coaching goal for this session (e.g. 'Zero red alerts at the Hairpin')",
    )

    goal_passed = models.BooleanField(
        null=True,
        blank=True,
        help_text="Whether the driver met the session goal — null if not yet evaluated",
    )

    started_at = models.DateTimeField(
        help_text="When the session began (first telemetry timestamp)",
    )

    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the session ended — null if still active",
    )

    @property
    def default_suggested_threshold(self) -> float:
        """
        Mode-based default suggested zone threshold for coaches:
        - Safety Mode -> 1.0g (conservative training limit)
        - Performance Mode -> 1.5g (pushing performance limit)
        """
        return 1.0 if self.mode == self.Mode.SAFETY else 1.5


    class Meta:
        db_table = "sessions"
        ordering = ["-started_at"]

    def __str__(self):
        return f"Session {self.id} — {self.driver.name} on {self.track.name}"


class Telemetry(models.Model):
    """
    A single telemetry reading from a kart's sensors during a session.

    Recorded at high frequency — each row is one data point with
    lateral g-force, speed, and GPS position. Composite index on
    session_id + recorded_at for efficient time-range queries.
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

    class Meta:
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


class Alert(models.Model):
    """
    A g-force threshold exceedance alert.

    Insert-only — alerts are never updated or deleted, creating a complete
    audit trail. Each alert records the measured g-value and the threshold
    that was applied at the time.
    """

    class Severity(models.TextChoices):
        AMBER = "amber", "Amber"
        RED = "red", "Red"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="alerts",
        help_text="The session during which this alert fired",
    )

    zone = models.ForeignKey(
        "tracks.Zone",
        on_delete=models.CASCADE,
        related_name="alerts",
        help_text="The zone where the threshold was exceeded",
    )

    severity = models.CharField(
        max_length=5,
        choices=Severity.choices,
        help_text="Alert severity — amber (approaching) or red (exceeded)",
    )

    g_value = models.FloatField(
        help_text="The actual g-force value that triggered the alert",
    )

    threshold_applied = models.FloatField(
        help_text="The threshold that was in effect when the alert fired — "
                  "may be a driver-specific custom threshold or the zone default",
    )

    triggered_at = models.DateTimeField(
        help_text="When the alert was triggered",
    )

    class Meta:
        db_table = "alerts"
        ordering = ["-triggered_at"]

    def __str__(self):
        return f"Alert {self.severity} — {self.zone.label} ({self.g_value}g)"


class BiometricReading(models.Model):
    """
    A biometric data point from the driver's wearable strap.

    Recorded alongside telemetry to correlate physical stress with
    driving behavior. Used by coaches to make pit/rest decisions.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="biometric_readings",
        help_text="The session this biometric reading belongs to",
    )

    recorded_at = models.DateTimeField(
        help_text="Timestamp of this biometric reading",
    )

    heart_rate = models.IntegerField(
        help_text="Heart rate in BPM",
    )

    spo2 = models.IntegerField(
        help_text="Blood oxygen saturation percentage (SpO2)",
    )

    breathing_rate = models.IntegerField(
        null=True,
        blank=True,
        help_text="Breathing rate in breaths per minute",
    )

    class Meta:
        db_table = "biometric_readings"
        ordering = ["session", "recorded_at"]

    def __str__(self):
        return f"Biometric {self.session_id} @ {self.recorded_at}"


class SessionNote(models.Model):
    """
    A coaching note attached to a session, optionally tied to a specific zone.

    Only coaches can create session notes. Notes are used for post-session
    review and debriefing with the driver.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="notes",
        help_text="The session this note is about",
    )

    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="session_notes",
        help_text="The coach who wrote this note",
    )

    zone = models.ForeignKey(
        "tracks.Zone",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="session_notes",
        help_text="Specific zone this note refers to (null for general session notes)",
    )

    note_text = models.TextField(
        help_text="The coaching note content",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this note was created",
    )

    class Meta:
        db_table = "session_notes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note by {self.coach.name} on session {self.session_id}"
