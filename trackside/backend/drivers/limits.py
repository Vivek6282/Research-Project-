"""
Trackside — The limit in force for a driver in a zone.

One rule used by alerting and by the demo run: the driver's newest
DriverZoneThreshold (newest updated_at wins), otherwise the zone's own default.
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
    """The limit in force for this driver and zone: the driver's newest own limit, else zone.threshold_g."""
    own = driver_limits_for_zones(driver_id, [zone.id])
    return own.get(zone.id, zone.threshold_g)
