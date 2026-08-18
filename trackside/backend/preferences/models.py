"""
Trackside — Preferences app models.

Server-stored user preferences for font size and tutorial completion state.
Stored server-side so preferences follow the user across devices —
not just localStorage.
"""

import uuid
from django.db import models
from django.conf import settings


class UserPreference(models.Model):
    """
    Per-user display preferences.

    Font size (4 fixed presets) and tutorial completion status are stored on
    the server so they persist across devices and sessions.
    """

    class FontSize(models.TextChoices):
        SMALL = "small", "Small"
        MEDIUM = "medium", "Medium"
        LARGE = "large", "Large"
        XLARGE = "xlarge", "Extra Large"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preferences",
        help_text="The user these preferences belong to",
    )

    font_size = models.CharField(
        max_length=10,
        choices=FontSize.choices,
        default=FontSize.MEDIUM,
        help_text="UI font size preset — small, medium, large, or xlarge",
    )

    tutorial_completed = models.BooleanField(
        default=False,
        help_text="Whether the user has completed or dismissed the per-role dashboard tutorial",
    )

    class Meta:
        db_table = "user_preferences"

    def __str__(self):
        return f"Preferences for {self.user.name}: {self.font_size}"

