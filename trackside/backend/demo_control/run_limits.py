"""
Trackside — Corner limits a demo run uses.

The simulator must show the same stages as the dashboards, so a run uses the limit
in force for the chosen driver (drivers/limits.py): the driver's newest own limit,
else the zone default.
"""

import math
from typing import Dict, List, Tuple

from drivers.limits import driver_limits_for_zones

# The only corners the built-in Demo Circuit run may set (fixed names, never taken from user input)
BUILTIN_CORNER_NAMES = ("Hairpin", "Sweeper", "Chicane")
# The range the simulator accepts for --limit
SIMULATOR_MIN_LIMIT = 0.50
SIMULATOR_MAX_LIMIT = 2.50


def run_limits(track, driver) -> Tuple[Dict[str, float], bool]:
    """({corner name: limit in force} for the track's active corners, True when any differs from the zone default)."""
    zones = list(track.zones.filter(is_active=True))
    own = driver_limits_for_zones(driver.id, [z.id for z in zones])
    limits = {z.label: own.get(z.id, z.threshold_g) for z in zones}
    is_custom = any(z.id in own and own[z.id] != z.threshold_g for z in zones)
    return limits, is_custom


def builtin_limit_args(track, driver) -> List[str]:
    """["--limit", "Name=value", ...] for Hairpin, Sweeper and Chicane whose limit in force differs from the zone default."""
    zones = {z.label.lower(): z for z in track.zones.filter(is_active=True)}
    own = driver_limits_for_zones(driver.id, [z.id for z in zones.values()])
    args: List[str] = []
    for name in BUILTIN_CORNER_NAMES:
        zone = zones.get(name.lower())
        value = own.get(zone.id) if zone else None
        valid = isinstance(value, (int, float)) and math.isfinite(value) and SIMULATOR_MIN_LIMIT <= value <= SIMULATOR_MAX_LIMIT
        if valid and value != zone.threshold_g:
            args += ["--limit", f"{name}={value:.3f}"]
    return args
