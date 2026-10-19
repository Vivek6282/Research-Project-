"""
Trackside Driving Sessions — Alert Model.
This module defines the insert-only Alert model recording lateral g-force threshold exceedances
and providing an immutable safety audit trail for coaches and race directors.
"""

import uuid
from django.db import models
from driving_sessions.models.session import Session


class Alert(models.Model):
    """
    A lateral g-force safety alert generated when telemetry exceeds a threshold.
    Insert-only design guarantees an immutable audit trail of on-track driving events.
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
        app_label = "driving_sessions"
        db_table = "alerts"
        ordering = ["-triggered_at"]

    def __str__(self):
        return f"Alert {self.severity} — {self.zone.label} ({self.g_value}g)"
