"""Trackside — Change a zone's g limit and record the change in the insert-only history."""

from tracks.models import Zone, ZoneThresholdHistory

SAME_LIMIT_TOLERANCE = 1e-9


def set_zone_limit(zone: Zone, new_limit_g: float, user) -> bool:
    """Set zone.threshold_g and add a history row when it really changes; returns True if changed."""
    if abs(zone.threshold_g - new_limit_g) <= SAME_LIMIT_TOLERANCE:
        return False
    ZoneThresholdHistory.objects.create(
        zone=zone, old_g=zone.threshold_g, new_g=new_limit_g,
        changed_by=user if getattr(user, "is_authenticated", False) else None,
    )
    zone.threshold_g = new_limit_g
    zone.save(update_fields=["threshold_g"])
    return True
