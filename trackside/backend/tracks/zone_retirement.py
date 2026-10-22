"""Trackside — Remove a corner (zone): delete it if it has no history, otherwise just deactivate it."""

from tracks.models import Zone

DELETED = "deleted"
DEACTIVATED = "deactivated"


def zone_has_history(zone: Zone) -> bool:
    """True when telemetry, alerts, notes or driver limits point at this zone (deleting would lose them)."""
    return (
        zone.telemetry_readings.exists()
        or zone.alerts.exists()
        or zone.session_notes.exists()
        or zone.driver_thresholds.exists()
    )


def retire_zone(zone: Zone) -> str:
    """Deactivate a zone that has history (hidden from new sessions) or delete one that has none."""
    if zone_has_history(zone):
        zone.is_active = False
        zone.save(update_fields=["is_active"])
        return DEACTIVATED
    zone.delete()
    return DELETED
