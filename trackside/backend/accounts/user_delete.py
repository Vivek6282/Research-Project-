"""
Trackside — Rules for permanently deleting a user.

What a delete removes (read from the model relations):
- a driver: their sessions with all readings, alerts, biometrics and notes on them, their own
  limits and preferences; devices assigned to them become unassigned;
- a coach: every session note they wrote (on anyone's session) and their preferences.
Audit entries are kept (their actor is cleared).
"""

from devices.models import Device
from drivers.models import DriverZoneThreshold
from driving_sessions.live_state import driver_is_live
from driving_sessions.models import Alert, BiometricReading, Session, SessionNote, Telemetry


def confirm_text_for(user) -> str:
    """The text an admin must type to confirm: the driver's code for a driver, otherwise the username."""
    if user.role == "driver" and user.driver_code:
        return user.driver_code
    return user.username or ""


def delete_counts(user) -> dict:
    """How many rows a delete of this user would remove (or unassign); equals what delete() really removes."""
    return {
        "sessions": Session.objects.filter(driver=user).count(),
        "telemetry_readings": Telemetry.objects.filter(session__driver=user).count(),
        "alerts": Alert.objects.filter(session__driver=user).count(),
        "biometric_readings": BiometricReading.objects.filter(session__driver=user).count(),
        "session_notes_on_their_sessions": SessionNote.objects.filter(session__driver=user).count(),
        "notes_written_by_them": SessionNote.objects.filter(coach=user).count(),
        "thresholds_set_for_them": DriverZoneThreshold.objects.filter(driver=user).count(),
        "devices_to_unassign": Device.objects.filter(assigned_to=user).count(),
    }


def blocked_reason(user, acting_admin):
    """Why this user must not be deleted right now (text), or None when the delete is allowed."""
    if user.pk == acting_admin.pk:
        return "You cannot delete your own account."
    if user.role == "admin":
        return "Admin accounts cannot be deleted."
    if user.role == "driver" and driver_is_live(user):
        return "This driver is live right now. Stop or wait for the run to end first."
    return None
