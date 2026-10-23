"""
Trackside — Skip readings that were already stored.

A device or the simulator retries a batch when an answer is lost (a timeout after the server already saved
it). Without a check, the retry stores every reading twice and inflates laps, corner times and maximum g.
A reading counts as already stored when the same session has one with the same time, lap, zone, g and speed.
"""

from driving_sessions.models import Telemetry


def reading_key(recorded_at, lap_number, zone_id, lateral_g, speed_kmh):
    """The facts that make two readings the same reading."""
    return (recorded_at, lap_number, zone_id, lateral_g, speed_kmh)


def drop_stored_duplicates(session, readings):
    """Split validated readings into (new ones, how many were skipped), also dropping repeats inside the batch."""
    if not readings:
        return [], 0
    stored = {
        reading_key(*row)
        for row in Telemetry.objects.filter(
            session=session, recorded_at__in=[r["recorded_at"] for r in readings],
        ).values_list("recorded_at", "lap_number", "zone_id", "lateral_g", "speed_kmh")
    }
    fresh = []
    for reading in readings:
        zone = reading.get("zone")
        key = reading_key(reading["recorded_at"], reading.get("lap_number"), zone.pk if zone else None,
                          reading["lateral_g"], reading["speed_kmh"])
        if key in stored:
            continue
        stored.add(key)
        fresh.append(reading)
    return fresh, len(readings) - len(fresh)
