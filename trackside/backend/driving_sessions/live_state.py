"""
Trackside — Is a driver live right now?

One rule shared by the roster status and by the user delete safeguard: a session is live when
it has not ended and its newest reading is recent (inside DRIVER_LIVE_WINDOW_SECONDS).
"""

from django.conf import settings
from django.utils import timezone

from driving_sessions.models import Session, Telemetry


def is_live_now(session, last_reading_at) -> bool:
    """True when the session is open and its newest reading arrived within the live window (5 s clock slack)."""
    if session is None or session.ended_at is not None or last_reading_at is None:
        return False
    window = getattr(settings, "DRIVER_LIVE_WINDOW_SECONDS", 30)
    seconds_ago = (timezone.now() - last_reading_at).total_seconds()
    return -5.0 <= seconds_ago <= window


def driver_is_live(driver) -> bool:
    """True when the driver's newest session is live right now."""
    latest = Session.objects.filter(driver=driver).order_by("-started_at").first()
    if latest is None:
        return False
    newest = Telemetry.objects.filter(session=latest).order_by("-recorded_at").values_list("recorded_at", flat=True).first()
    return is_live_now(latest, newest)
