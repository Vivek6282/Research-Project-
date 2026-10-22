"""
Trackside — Extra fields for live telemetry events.

The Coach screen needs the limit in force, the stage and the corner of each reading.
They are worked out on the server with the same rules as the alerts and are added to
the live WebSocket event only (never stored, never in the REST output).
"""

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Dict, Optional

from driving_sessions.alerting import stage_for
from drivers.limits import limit_in_force

# Names the Coach screen uses for the alert stages
STAGE_NAMES = {"red": "intervene", "amber": "monitoring", None: "nominal"}

_zone_cache: ContextVar[Optional[Dict]] = ContextVar("live_zone_cache", default=None)


@contextmanager
def live_event_cache():
    """Share zone and limit lookups between all readings saved inside this block (one request)."""
    token = _zone_cache.set({})
    try:
        yield
    finally:
        _zone_cache.reset(token)


def zone_facts(reading) -> Dict:
    """{limit, zone_label, corner_type} of the reading's zone, looked up once per (driver, zone) while a cache is open."""
    cache = _zone_cache.get()
    key = (reading.session.driver_id, reading.zone_id)
    if cache is not None and key in cache:
        return cache[key]
    zone = reading.zone
    facts = {
        "limit": limit_in_force(key[0], zone),
        "zone_label": zone.label,
        "corner_type": zone.corner_type,
    }
    if cache is not None:
        cache[key] = facts
    return facts


def live_fields(reading) -> Dict:
    """threshold, stage, zone_label and corner_type for one reading; a straight has no limit and is nominal."""
    if not reading.zone_id:
        return {"threshold": None, "stage": "nominal", "zone_label": None, "corner_type": None}
    facts = zone_facts(reading)
    return {
        "threshold": facts["limit"],
        "stage": STAGE_NAMES[stage_for(reading.lateral_g, facts["limit"])],
        "zone_label": facts["zone_label"],
        "corner_type": facts["corner_type"],
    }
