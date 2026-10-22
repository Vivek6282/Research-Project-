"""
Trackside — The limit in force in a zone.

The map is the only place that sets g-force limits: a corner's limit is zone.threshold_g
(edited on the Maps screen) and applies to everyone who drives it. Old per-driver rows
(DriverZoneThreshold) are kept as history and ignored.
"""

from typing import Optional


def limit_in_force(driver_id, zone) -> Optional[float]:
    """The limit in force in this zone: the corner's own limit, zone.threshold_g. driver_id is ignored (kept so callers do not break)."""
    return zone.threshold_g
