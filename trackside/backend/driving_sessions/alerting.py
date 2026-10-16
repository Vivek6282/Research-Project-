"""
Trackside — Alerting logic for telemetry ingestion.

Computes alert stages, monitors g-force threshold crossings, and
creates Alert records inside an atomic transaction.
"""

from typing import Optional, List, Dict
from django.db import transaction
from django.contrib.auth import get_user_model
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from driving_sessions.models import Session, Telemetry, Alert
from tracks.models import Zone
from drivers.models import DriverZoneThreshold

User = get_user_model()


def stage_for(g: float, threshold: float) -> Optional[str]:
    """
    Determine the alerting stage for a given g-force and threshold:
    - g >= threshold -> 'red'
    - g >= 0.82 * threshold -> 'amber'
    - otherwise -> None
    """
    if threshold is None or threshold <= 0:
        return None
    if g >= threshold:
        return "red"
    elif g >= 0.82 * threshold:
        return "amber"
    return None


def process_telemetry_alerts(session: Session, new_readings: List[Telemetry]) -> List[Alert]:
    """
    Process newly ingested telemetry readings for a session and generate Alert rows.
    Must be called inside transaction.atomic.

    Alert rules:
    - Stage evaluation: stage_for(g, threshold) (82% rule).
    - Threshold: driver's newest DriverZoneThreshold for that zone (newest wins),
      otherwise zone.threshold_g.
    - No zone (straight): no alert, and the alerting state resets.
    - ONE alert per crossing: create an Alert when the stage rises compared with
      the previous reading of the same session. amber -> red creates a new red alert.
      Staying in the same stage creates nothing. Dropping below amber (or a straight)
      resets.
    - For the first reading of a request, continue from the latest stored reading
      of that session.
    - Uses bulk_create and caches zone/threshold lookups per request.
    """
    if not new_readings:
        return []

    # 1. Sort incoming readings in recorded_at order
    sorted_readings = sorted(new_readings, key=lambda r: r.recorded_at)

    # 2. Get latest stored reading of the session before this batch
    new_ids = [r.id for r in sorted_readings if getattr(r, "id", None)]
    latest_stored = (
        Telemetry.objects.filter(session=session)
        .exclude(id__in=new_ids)
        .order_by("-recorded_at")
        .first()
    )

    # 3. Cache zones and custom thresholds
    zone_ids = set()
    for r in sorted_readings:
        if r.zone_id:
            zone_ids.add(r.zone_id)
    if latest_stored and latest_stored.zone_id:
        zone_ids.add(latest_stored.zone_id)

    zones_map: Dict[str, Zone] = {}
    if zone_ids:
        for z in Zone.objects.filter(id__in=zone_ids):
            zones_map[z.id] = z

    thresholds_map: Dict[str, float] = {}
    if zone_ids and session.driver_id:
        # Ordering by updated_at ascending ensures the latest row overwrites in dict
        custom_thresholds = (
            DriverZoneThreshold.objects.filter(
                driver_id=session.driver_id,
                zone_id__in=zone_ids,
            ).order_by("updated_at")
        )
        for dzt in custom_thresholds:
            thresholds_map[dzt.zone_id] = dzt.custom_threshold_g

    def get_effective_threshold(zone_id) -> Optional[float]:
        if not zone_id:
            return None
        if zone_id in thresholds_map:
            return thresholds_map[zone_id]
        zone = zones_map.get(zone_id)
        return zone.threshold_g if zone else None

    # 4. Determine initial prev_stage and prev_zone_id from latest_stored reading
    prev_zone_id: Optional[str] = None
    prev_stage: Optional[str] = None
    if latest_stored and latest_stored.zone_id:
        prev_zone_id = latest_stored.zone_id
        thresh = get_effective_threshold(latest_stored.zone_id)
        if thresh is not None:
            prev_stage = stage_for(latest_stored.lateral_g, thresh)

    alerts_to_create: List[Alert] = []

    # 5. Process readings in recorded_at order
    for reading in sorted_readings:
        if not reading.zone_id:
            # Straight resets the alerting state
            prev_stage = None
            prev_zone_id = None
            continue

        thresh = get_effective_threshold(reading.zone_id)
        if thresh is None:
            prev_stage = None
            prev_zone_id = None
            continue

        # If entering a different zone, reset prev_stage for the new zone
        if reading.zone_id != prev_zone_id:
            prev_stage = None

        curr_stage = stage_for(reading.lateral_g, thresh)

        # Check stage rises
        if curr_stage == "amber" and prev_stage is None:
            alerts_to_create.append(
                Alert(
                    session=session,
                    zone=zones_map.get(reading.zone_id) or reading.zone,
                    severity=Alert.Severity.AMBER,
                    g_value=reading.lateral_g,
                    threshold_applied=thresh,
                    triggered_at=reading.recorded_at,
                )
            )
        elif curr_stage == "red" and prev_stage != "red":
            alerts_to_create.append(
                Alert(
                    session=session,
                    zone=zones_map.get(reading.zone_id) or reading.zone,
                    severity=Alert.Severity.RED,
                    g_value=reading.lateral_g,
                    threshold_applied=thresh,
                    triggered_at=reading.recorded_at,
                )
            )

        prev_stage = curr_stage
        prev_zone_id = reading.zone_id

    # 6. Bulk create alerts
    created_alerts = []
    if alerts_to_create:
        created_alerts = Alert.objects.bulk_create(alerts_to_create)
        # Broadcast newly created alerts to WebSocket clients if channel layer is available
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                from driving_sessions.serializers import AlertSerializer
                for alert in created_alerts:
                    data = AlertSerializer(alert).data
                    async_to_sync(channel_layer.group_send)(
                        f"session_{alert.session_id}",
                        {
                            "type": "alert_triggered",
                            "data": data,
                        },
                    )
        except Exception:
            pass

    return created_alerts
