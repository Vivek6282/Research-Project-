"""
Trackside — Drivers app models.

Manages driver-specific zone thresholds. These are insert-only (append-only
history) — coaches can lower a driver's threshold below the zone default
but never raise it above the zone's calibrated safe limit.
"""

import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class DriverZoneThreshold(models.Model):
    """
    A custom g-force threshold set by a coach for a specific driver in a zone.

    INSERT-ONLY: threshold history is never updated in place. Each new
    threshold creates a new row, and the latest row (by updated_at) is
    the active threshold for that driver+zone pair.

    The custom_threshold_g must be ≤ the zone's calibrated threshold_g —
    coaches can make thresholds stricter but never more lenient than the
    safety-calibrated limit.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="zone_thresholds",
        help_text="The driver this custom threshold applies to",
    )

    zone = models.ForeignKey(
        "tracks.Zone",
        on_delete=models.CASCADE,
        related_name="driver_thresholds",
        help_text="The zone this custom threshold applies to",
    )

    custom_threshold_g = models.FloatField(
        help_text="Custom g-force threshold — must be ≤ zone.threshold_g",
    )

    set_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="thresholds_set",
        help_text="The coach who set this threshold",
    )

    updated_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this threshold was set — latest row is the active threshold",
    )

    class Meta:
        db_table = "driver_zone_thresholds"
        ordering = ["-updated_at"]

    def clean(self):
        """
        Validate that the custom threshold doesn't exceed the zone's
        calibrated safe limit. This runs on save — also enforced in
        the serializer for API requests.
        """
        if self.zone and self.custom_threshold_g > self.zone.threshold_g:
            raise ValidationError(
                f"Custom threshold ({self.custom_threshold_g}g) cannot exceed "
                f"the zone's calibrated limit ({self.zone.threshold_g}g)."
            )

    def save(self, *args, **kwargs):
        """Run validation before saving."""
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.driver.name} — {self.zone.label}: "
            f"{self.custom_threshold_g}g"
        )
