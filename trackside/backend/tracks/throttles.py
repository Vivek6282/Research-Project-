"""Trackside — Rate limits for the track import endpoints."""

from rest_framework.throttling import UserRateThrottle


class TrackImportPreviewThrottle(UserRateThrottle):
    """At most 10 import previews per hour per user (rate set in settings)."""

    scope = "track_import"


class TrackImportConfirmThrottle(UserRateThrottle):
    """At most 10 saved imports per hour per user (rate set in settings)."""

    scope = "track_import_confirm"
