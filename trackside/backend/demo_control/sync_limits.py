"""
Trackside Demo Control — Backend Limit Synchronization.
This module synchronizes coach corner threshold limits with DriverZoneThreshold models
for simulated driving sessions.
"""

import os
import uuid
from dotenv import dotenv_values
from django.conf import settings
from django.db import transaction
from django.core.exceptions import ValidationError

from drivers.models import DriverZoneThreshold
from driving_sessions.models import Session
from tracks.models import Zone
from demo_control.simulator import LIMIT_RANGES


def sync_limits_to_backend(limits_dict, user):
    """
    Syncs custom corner limits to DriverZoneThreshold in the backend.
    Reads SESSION_ID from trackside/demo/.env via dotenv_values (never in os.environ).
    Returns (limits_synced: bool, limits_note: str | None).
    """
    demo_env_path = os.path.abspath(
        os.path.join(settings.BASE_DIR.parent, "demo", ".env")
    )
    demo_env = dotenv_values(demo_env_path) if os.path.exists(demo_env_path) else {}
    session_id_raw = demo_env.get("SESSION_ID")

    if not session_id_raw or not str(session_id_raw).strip():
        return False, "SESSION_ID not configured in trackside/demo/.env"

    try:
        session_uuid = uuid.UUID(str(session_id_raw).strip())
    except (ValueError, AttributeError):
        return False, f"SESSION_ID '{session_id_raw}' is not a valid UUID"

    try:
        session = Session.objects.select_related("track", "driver").get(id=session_uuid)
    except Session.DoesNotExist:
        return False, f"Session '{session_id_raw}' not found"

    if not session.track:
        return False, f"Session '{session_id_raw}' has no associated track"

    if not session.driver:
        return False, f"Session '{session_id_raw}' has no associated driver"

    zones_map = {}
    for corner in ["Hairpin", "Sweeper", "Chicane"]:
        zone = Zone.objects.filter(track=session.track, label__iexact=corner).first()
        if not zone:
            return False, f"Zone '{corner}' not found on track '{session.track.name}'"
        zones_map[corner] = zone

    try:
        with transaction.atomic():
            for corner in ["Hairpin", "Sweeper", "Chicane"]:
                zone = zones_map[corner]
                req_limit = float(limits_dict.get(corner, LIMIT_RANGES[corner]["default"]))

                latest_dt = (
                    DriverZoneThreshold.objects.filter(driver=session.driver, zone=zone)
                    .order_by("-updated_at")
                    .first()
                )
                active_threshold = (
                    latest_dt.custom_threshold_g if latest_dt else zone.threshold_g
                )

                if abs(req_limit - active_threshold) > 1e-4:
                    new_dt = DriverZoneThreshold(
                        driver=session.driver,
                        zone=zone,
                        custom_threshold_g=req_limit,
                        set_by=user,
                    )
                    new_dt.full_clean()
                    new_dt.save()
        return True, None
    except ValidationError as ve:
        err_msg = "; ".join(ve.messages) if hasattr(ve, "messages") else str(ve)
        return False, f"Validation error during limits sync: {err_msg}"
    except Exception as e:
        return False, f"Failed to sync limits: {str(e)}"
