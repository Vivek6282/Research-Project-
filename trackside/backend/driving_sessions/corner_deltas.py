"""
Trackside — Corner times and deltas of one session (K1).

Corner times are measured per crossing, not per lap number: a crossing is one
unbroken run of readings inside the same corner, in time order. Its time is the
last reading time minus the first, plus one reading interval (the median gap
between the session's consecutive readings). This keeps a corner that spans the
start/finish line in one piece. A crossing belongs to the lap it was entered on.
Only completed laps count towards a corner's best; the lap in progress is listed
but never becomes the best.
"""

from datetime import datetime
from statistics import median
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from driving_sessions.models import Session, Telemetry

DECIMALS = 3
# A gap longer than this between two readings ends a crossing (data loss, pit stop)
MAX_GAP_IN_CROSSING_S = 3.0
# Leaving a corner for at most this long and coming back counts as the same crossing (GPS flicker)
FLICKER_MERGE_S = 1.0


def reading_interval_s(times: Iterable[datetime]) -> float:
    """Median gap in seconds between consecutive readings (0.0 when there are fewer than two)."""
    gaps, previous = [], None
    for moment in times:
        if previous is not None:
            gaps.append((moment - previous).total_seconds())
        previous = moment
    return float(median(gaps)) if gaps else 0.0


def split_into_crossings(readings: Iterable[Tuple[datetime, Optional[str], Optional[int]]]) -> List[dict]:
    """Group time-ordered (time, zone id, lap) readings into crossings: unbroken runs inside one corner."""
    crossings: List[dict] = []
    current, previous_time = None, None
    for moment, zone_id, lap in readings:
        gap_too_long = previous_time is not None and (moment - previous_time).total_seconds() > MAX_GAP_IN_CROSSING_S
        previous_time = moment
        if current is not None and (zone_id != current["zone_id"] or gap_too_long):
            crossings.append(current)
            current = None
        if zone_id is None:
            continue
        if current is None:
            current = {"zone_id": zone_id, "first": moment, "last": moment, "lap": lap}
        current["last"] = moment
        if current["lap"] is None:
            current["lap"] = lap
    if current is not None:
        crossings.append(current)
    return merge_flicker(crossings)


def merge_flicker(crossings: List[dict]) -> List[dict]:
    """Join a crossing to the previous one when it is the same corner re-entered within FLICKER_MERGE_S."""
    merged: List[dict] = []
    for crossing in crossings:
        before = merged[-1] if merged else None
        if (before is not None and before["zone_id"] == crossing["zone_id"]
                and (crossing["first"] - before["last"]).total_seconds() <= FLICKER_MERGE_S):
            before["last"] = crossing["last"]
            before["lap"] = before["lap"] if before["lap"] is not None else crossing["lap"]
        else:
            merged.append(crossing)
    return merged


def corner_lap_spans(session: Session) -> Dict[Tuple[str, int], Tuple[datetime, datetime]]:
    """First and last reading time of each corner's first crossing on each lap (crossings with no lap are skipped)."""
    readings = (Telemetry.objects.filter(session=session).order_by("recorded_at")
                .values_list("recorded_at", "zone_id", "lap_number").iterator())
    spans: Dict[Tuple[str, int], Tuple[datetime, datetime]] = {}
    for crossing in split_into_crossings((t, str(z) if z else None, lap) for t, z, lap in readings):
        key = (crossing["zone_id"], crossing["lap"])
        if crossing["lap"] is not None and key not in spans:
            spans[key] = (crossing["first"], crossing["last"])
    return spans


def completed_lap_numbers(session: Session) -> Tuple[set, set]:
    """(all lap numbers seen, the ones that are completed: a later lap exists, or the session has ended)."""
    laps = set(Telemetry.objects.filter(session=session, lap_number__isnull=False)
               .values_list("lap_number", flat=True).distinct())
    last = max(laps) if laps else None
    return laps, {n for n in laps if session.ended_at is not None or n != last}


def corner_entry(zone, times: Dict[int, float], completed: set) -> dict:
    """One corner: its laps, best over completed laps, last completed lap and deltas (null with fewer than 2 completed laps)."""
    done = {n: t for n, t in times.items() if n in completed}
    best = min(done.values()) if done else None
    comparable = best is not None and len(done) >= 2

    def delta(seconds):
        """Seconds slower than the best (positive = slower), or None when there is nothing to compare."""
        return round(seconds - best, DECIMALS) if comparable else None

    last_lap = max(done) if done else None
    return {
        "zone_id": str(zone.id), "label": zone.label,
        "best_s": round(best, DECIMALS) if best is not None else None,
        "last_lap_s": round(done[last_lap], DECIMALS) if done else None,
        "last_lap_delta_s": delta(done[last_lap]) if done else None,
        "laps": [{"lap_number": n, "time_s": round(times[n], DECIMALS), "delta_s": delta(times[n]),
                  "completed": n in completed} for n in sorted(times)],
    }


def lap_order_key(zone, times: Dict[int, float], first_seen: Dict[str, datetime]):
    """Sort corners in the order the kart meets them; corners with no data go last, by name."""
    seen = first_seen.get(str(zone.id))
    return (seen is None, seen or datetime.max, zone.label)


def build_corner_deltas(session: Session, zones: Sequence) -> List[dict]:
    """Corner times and deltas for the given (active) zones of the session's track."""
    spans = corner_lap_spans(session)
    interval = reading_interval_s(Telemetry.objects.filter(session=session).order_by("recorded_at")
                                  .values_list("recorded_at", flat=True).iterator())
    _, completed = completed_lap_numbers(session)
    first_seen: Dict[str, datetime] = {}
    per_zone: Dict[str, Dict[int, float]] = {}
    for (zone_id, lap), (first, last) in spans.items():
        per_zone.setdefault(zone_id, {})[lap] = (last - first).total_seconds() + interval
        if zone_id not in first_seen or first < first_seen[zone_id]:
            first_seen[zone_id] = first
    ordered = sorted(zones, key=lambda z: lap_order_key(z, per_zone.get(str(z.id), {}), first_seen))
    return [corner_entry(z, per_zone.get(str(z.id), {}), completed) for z in ordered]
