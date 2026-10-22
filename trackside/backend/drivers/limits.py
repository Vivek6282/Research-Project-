"""
Trackside — The limit in force in a zone.

The map is the only place that sets g-force limits: a corner's limit is zone.threshold_g
(edited on the Maps screen) and applies to everyone who drives it. Old per-driver rows
(DriverZoneThreshold) are kept as history and ignored.
"""

from typing import Dict, Iterable, Optional

from drivers.models import DriverZoneThreshold


def driver_limits_for_zones(driver_id, zone_ids: Iterable) -> Dict:
    """The driver's own newest limit for each of the given zones; zones with no own limit are left out."""
    zone_ids = list(zone_ids)
    if not driver_id or not zone_ids:
        return {}
    newest_last = DriverZoneThreshold.objects.filter(driver_id=driver_id, zone_id__in=zone_ids).order_by("updated_at")
    return {row.zone_id: row.custom_threshold_g for row in newest_last}


def limit_in_force(driver_id, zone) -> Optional[float]:
    """The limit in force in this zone: the corner's own limit, zone.threshold_g. driver_id is ignored (kept so callers do not break)."""
    return zone.threshold_g
