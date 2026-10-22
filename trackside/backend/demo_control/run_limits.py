"""
Trackside — Corner limits a demo run uses.

The map is the only place that sets g-force limits, so a run uses each corner's own limit
(zone.threshold_g, set on the Maps screen). The built-in Demo Circuit run uses the simulator's
own track and fixed defaults, so no --limit arguments are passed for it.
"""

from typing import Dict

from drivers.limits import limit_in_force


def run_limits(track) -> Dict[str, float]:
    """{corner name: the map's limit} for the track's active corners, shown in the demo status."""
    return {z.label: limit_in_force(None, z) for z in track.zones.filter(is_active=True)}
