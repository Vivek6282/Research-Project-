"""
Trackside Demo Control — Start, stop and clean up one Coach demo run (H4).

One run = one demo Session (is_demo) on the chosen map for the chosen driver, played
by one dedicated device ("Demo kart unit") that is assigned to that driver only for
the length of the run, with a fresh API token that is thrown away afterwards.
"""

import json
import uuid

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from demo_control import simulator
from demo_control.simulator import is_hosted_demo_enabled, is_production_environment
from devices.models import Device
from devices.serializers import DeviceSerializer
from driving_sessions.models import Session
from driving_sessions.session_close import close_session_if_open
from tracks.demo_circuit_setup import ensure_demo_circuit
from tracks.models import Track
from demo_control.run_limits import run_limits
from tracks.outline_gps import write_schematic_gps_file
from tracks.track_profile import ProfileError, write_track_profile

DEMO_DEVICE_NAME = "Demo kart unit"
PACES = ("safe", "edge", "over")
MIN_LAPS, MAX_LAPS = 1, 20


class DemoRunError(Exception):
    """The run cannot start (or stop); the message is shown to the coach."""

    def __init__(self, message: str, status_code: int = 400):
        """Keep the user-facing message and the HTTP status to answer with."""
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# Post every reading on its own so the Coach screen moves smoothly (a fixed value, never taken from the request)
POST_BATCH_ARGS = ["--post-batch", "1"]


def profile_directory() -> str:
    """The fixed server folder for track profile files (backend/demo_profiles)."""
    return str(settings.BASE_DIR / "demo_profiles")


def parse_uuid(value, what: str) -> uuid.UUID:
    """Read a UUID from the request or raise a clear 400."""
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        raise DemoRunError(f"{what} is not valid.")


def parse_start_request(data) -> dict:
    """Check map, driver, laps and pace; returns the objects to use."""
    from django.contrib.auth import get_user_model

    track = Track.objects.filter(pk=parse_uuid(data.get("track_id"), "track_id")).first()
    if track is None:
        raise DemoRunError("That map does not exist.")
    if track.is_archived:
        raise DemoRunError("That map is archived. Restore it first.")
    driver = get_user_model().objects.filter(pk=parse_uuid(data.get("driver_id"), "driver_id")).first()
    if driver is None or driver.role != "driver":
        raise DemoRunError("Choose a driver.")
    if not driver.is_active:
        raise DemoRunError(f"{driver.name} is deactivated. Choose an active driver.")
    laps = data.get("laps")
    if type(laps) is not int or not (MIN_LAPS <= laps <= MAX_LAPS):
        raise DemoRunError(f"laps must be a whole number from {MIN_LAPS} to {MAX_LAPS}.")
    pace = data.get("pace", "safe")
    if not isinstance(pace, str) or pace not in PACES:
        raise DemoRunError("pace must be safe, edge or over.")
    return {"track": track, "driver": driver, "laps": laps, "pace": pace}


def get_demo_device() -> Device:
    """The one dedicated demo kart unit, created the first time it is needed."""
    device = Device.objects.filter(name=DEMO_DEVICE_NAME, device_type=Device.DeviceType.KART_UNIT).first()
    return device or Device.objects.create(name=DEMO_DEVICE_NAME, device_type=Device.DeviceType.KART_UNIT)


def check_driver_has_no_other_kart_unit(driver, demo_device: Device) -> None:
    """Refuse when the driver already holds a different kart unit, and say which one."""
    other = (Device.objects.filter(assigned_to=driver, device_type=Device.DeviceType.KART_UNIT)
             .exclude(pk=demo_device.pk).first())
    if other:
        label = other.name or f"kart unit {str(other.id)[:8]}"
        raise DemoRunError(
            f"{driver.name} already has {label}. Unassign it in Admin > Devices, or choose another driver.", 409,
        )


def assign_device(device: Device, driver, request) -> None:
    """Move the demo device to a driver (or to nobody) through the normal assignment rules and audit log."""
    serializer = DeviceSerializer(
        device, data={"assigned_to": str(driver.id) if driver else None},
        partial=True, context={"request": request},
    )
    try:
        serializer.is_valid(raise_exception=True)
    except serializers.ValidationError as error:
        raise DemoRunError(f"Could not assign the demo device: {error.detail}", 409)
    serializer.save()


def release_demo_device(request) -> None:
    """Unassign the demo device and invalidate its token (safe to call when nothing is assigned)."""
    device = Device.objects.filter(name=DEMO_DEVICE_NAME, device_type=Device.DeviceType.KART_UNIT).first()
    if device is None:
        return
    if device.assigned_to_id:
        assign_device(device, None, request)
    Device.objects.filter(pk=device.pk).update(api_key_hash="")


def finalize_run(request) -> bool:
    """Clean up a run whose process has ended: close its session, unassign the device, drop the token."""
    info = simulator.get_run_info()
    if info is None or info.get("finalized") or simulator.is_simulator_running():
        return False
    close_session_if_open(info["session_id"])
    release_demo_device(request)
    simulator.mark_run_finalized()
    return True


def release_orphans(request) -> None:
    """After a server restart: close demo sessions left open and release the demo device."""
    if simulator.is_simulator_running():
        return
    for session in Session.objects.filter(is_demo=True, ended_at__isnull=True):
        close_session_if_open(session.pk)
    release_demo_device(request)


def zone_map_for(track: Track) -> dict:
    """{corner name: zone id} for the simulator, so its readings are stored against the right zones."""
    return {zone.label: str(zone.id) for zone in track.zones.filter(is_active=True)}


def start_demo_run(request) -> dict:
    """Validate, prepare the session, device, token and profile, then launch the simulator."""
    finalize_run(request)
    release_orphans(request)
    if simulator.is_simulator_running():
        raise DemoRunError("A demo is already running. Stop it first.", 409)
    chosen = parse_start_request(request.data)
    track, driver, laps, pace = chosen["track"], chosen["driver"], chosen["laps"], chosen["pace"]

    if track.is_builtin:
        track = ensure_demo_circuit()
        gps_path = write_schematic_gps_file(profile_directory(), track.id)
        extra_args = ["--laps", str(laps), "--gps-file", gps_path] + POST_BATCH_ARGS
    else:
        try:
            profile_path = write_track_profile(track, profile_directory(), driver)
        except ProfileError as error:
            raise DemoRunError(str(error))
        extra_args = ["--laps", str(laps), "--track-file", profile_path, "--pace", pace] + POST_BATCH_ARGS
    if is_production_environment() and is_hosted_demo_enabled():
        extra_args.append("--dry-run")  # a hosted server has no bridge: the Coach's browser forwards the stages to it
    zones = zone_map_for(track)
    if not zones:
        raise DemoRunError("This map has no corners yet. Open 'Edit corners' and add some first.")

    with transaction.atomic():
        device = get_demo_device()
        check_driver_has_no_other_kart_unit(driver, device)
        assign_device(device, driver, request)
        raw_token = device.set_api_key()
        device.save(update_fields=["api_key_hash"])
        session = Session.objects.create(
            driver=driver, track=track, mode=Session.Mode.PERFORMANCE, started_at=timezone.now(),
            kart_number="Demo", is_demo=True,
        )
    limits = run_limits(track)
    run_values = {
        "SESSION_ID": str(session.id), "DEVICE_TOKEN": raw_token,
        "BACKEND_URL": f"{request.scheme}://{request.get_host()}", "DEMO_ZONES": json.dumps(zones),
    }
    run_info = {
        "session_id": str(session.id), "device_id": str(device.id), "driver_id": str(driver.id),
        "driver_name": driver.name, "track_id": str(track.id), "track_name": track.name, "laps": laps,
        "pace": pace, "pace_applied": not track.is_builtin, "built_in": track.is_builtin, "limits": limits,
        "finalized": False,
    }
    try:
        pid = simulator.start_simulator(extra_args, run_values, run_info)
    except simulator.AlreadyRunningError:
        raise DemoRunError("A demo is already running. Stop it first.", 409)
    except Exception as error:
        close_session_if_open(session.pk)
        release_demo_device(request)
        raise DemoRunError(f"Failed to start the simulator: {error}", 500)
    return {"status": "started", "pid": pid, **{k: v for k, v in run_info.items() if k != "finalized"}}


def stop_demo_run(request) -> bool:
    """Stop the simulator (idempotent), then close the session and release the device."""
    was_running = simulator.stop_simulator()
    finalize_run(request)
    return was_running


def current_status(request) -> dict:
    """The status panel data; also cleans up after a run that has just ended."""
    finalize_run(request)
    return simulator.get_simulator_status()
