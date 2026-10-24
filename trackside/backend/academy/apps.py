"""Trackside — Academy-wide settings (Phase 2.0: data retention)."""

from django.apps import AppConfig


class AcademyConfig(AppConfig):
    """Registers the academy settings app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "academy"
