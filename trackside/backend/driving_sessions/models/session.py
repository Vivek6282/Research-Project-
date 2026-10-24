"""
Trackside Driving Sessions — Session and Coaching Note Models.
This module defines the Session lifecycle model (driving sessions on track with mode and goals)
and SessionNote model for post-session coach debriefings.
"""

import uuid
from django.db import models
from django.conf import settings


class Session(models.Model):
    """
    A driving session representing on-track driving activity between start and end.
    Each session operates in a designated mode (safety or performance) with an optional coaching goal.
    """

    class Mode(models.TextChoices):
        SAFETY = "safety", "Safety"
        PERFORMANCE = "performance", "Performance"

    class DataSource(models.TextChoices):
        SIMULATOR = "simulator", "Simulator"
        REAL_TIME = "real_time", "Real time"

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

    kart_number = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Kart identifier (e.g. '#12')",
    )

    is_demo = models.BooleanField(
        default=False,
        help_text="True for runs started from the Coach Maps & Demo tab (simulated, not real driving)",
    )

    # Phase 2.1: where this session's readings come from, set by the coach
    data_source = models.CharField(
        max_length=12,
        choices=DataSource.choices,
        default=DataSource.SIMULATOR,
        help_text="simulator: the lap simulator or a device feeds it; real_time: the driver's phone page feeds it",
    )

    phone_calibration = models.JSONField(
        null=True,
        blank=True,
        help_text="The phone's mounting found at calibration: gravity and forward directions (phone axes)",
    )

    sensor_flags = models.JSONField(
        default=list,
        blank=True,
        help_text="Warnings raised by the phone during the session, e.g. sensor_disagreement, mount_moved",
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
        app_label = "driving_sessions"
        db_table = "sessions"
        ordering = ["-started_at"]

    def __str__(self):
        return f"Session {self.id} — {self.driver.name} on {self.track.name}"


class SessionNote(models.Model):
    """
    A coaching debrief note attached to a session, optionally linked to a specific zone.
    Security rule: Only coaches can author session notes.
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
        app_label = "driving_sessions"
        db_table = "session_notes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note by {self.coach.name} on session {self.session_id}"
