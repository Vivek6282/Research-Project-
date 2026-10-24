"""
Trackside — Academy settings: one row for the whole academy (Phase 2.0).

Holds how long recorded data is kept. The purge command
(`manage.py purge_expired_data`) deletes data older than this.
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

DEFAULT_RETENTION_MONTHS = 12
MIN_RETENTION_MONTHS = 1
MAX_RETENTION_MONTHS = 120


class AcademySettings(models.Model):
    """The single settings row; always read it with AcademySettings.current()."""

    retention_months = models.PositiveSmallIntegerField(
        default=DEFAULT_RETENTION_MONTHS,
        validators=[MinValueValidator(MIN_RETENTION_MONTHS), MaxValueValidator(MAX_RETENTION_MONTHS)],
        help_text="Telemetry, device events and biometric readings older than this many months are purged",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
        help_text="The admin who last changed the settings",
    )

    class Meta:
        verbose_name_plural = "academy settings"

    @classmethod
    def current(cls) -> "AcademySettings":
        """The one settings row, created with the defaults the first time it is needed."""
        settings_row, _ = cls.objects.get_or_create(pk=1)
        return settings_row

    def save(self, *args, **kwargs):
        """Always store as row 1, so there can never be two settings rows."""
        self.pk = 1
        super().save(*args, **kwargs)
