"""
Trackside — Laptop link (a laptop's simulator feeds a hosted session).

The glove only talks to the bridge on a laptop, so on a hosted site the laptop's simulator does both
jobs: it drives the glove and posts its readings to the server. This module prepares that: it creates
a live sample session on the built-in Demo Circuit for a chosen driver, assigns a dedicated
"Laptop link unit" device and returns its access token ONCE. The token is the device's token: it can
only post readings and finish sessions of the driver the device is assigned to, and it is invalidated
when the link ends. Coach and Admin only. The server never runs the simulator.
"""

from django.utils import timezone
from django.db import transaction

from demo_control.demo_run import DemoRunError, assign_device, check_driver_has_no_other_kart_unit
from devices.models import Device
from driving_sessions.models import Session, Telemetry
from driving_sessions.session_close import close_session_if_open
from tracks.demo_circuit_setup import ensure_demo_circuit

LAPTOP_DEVICE_NAME = "Laptop link unit"
LAPTOP_KART = "Laptop"
RECEIVING_WINDOW_SECONDS = 15


def laptop_device() -> Device:
    """The dedicated laptop-link kart unit, created the first time it is needed."""
    device = Device.objects.filter(name=LAPTOP_DEVICE_NAME, device_type=Device.DeviceType.KART_UNIT).first()
    return device or Device.objects.create(name=LAPTOP_DEVICE_NAME, device_type=Device.DeviceType.KART_UNIT)


def open_link_session():
    """The link session that has not ended yet, or None."""
    return (Session.objects.filter(is_demo=True, kart_number=LAPTOP_KART, ended_at__isnull=True)
            .select_related("driver").order_by("-started_at").first())


def end_link(request) -> None:
    """Close any open link session, unassign the device and invalidate its token (safe to call any time)."""
    for session in Session.objects.filter(is_demo=True, kart_number=LAPTOP_KART, ended_at__isnull=True):
        close_session_if_open(session.pk)
    device = Device.objects.filter(name=LAPTOP_DEVICE_NAME, device_type=Device.DeviceType.KART_UNIT).first()
    if device is None:
        return
    if device.assigned_to_id:
        assign_device(device, None, request)
    Device.objects.filter(pk=device.pk).update(api_key_hash="")


def start_link(request, driver) -> dict:
    """Create the live session and the one-time token for this driver; returns what the laptop needs."""
    if driver is None or driver.role != "driver":
        raise DemoRunError("Choose a driver.")
    if not driver.is_active:
        raise DemoRunError(f"{driver.name} is deactivated. Choose an active driver.")
    end_link(request)  # one link at a time
    track = ensure_demo_circuit()
    zones = {z.label: str(z.id) for z in track.zones.filter(is_active=True)}
    with transaction.atomic():
        device = laptop_device()
        check_driver_has_no_other_kart_unit(driver, device)
        assign_device(device, driver, request)
        raw_token = device.set_api_key()
        device.save(update_fields=["api_key_hash"])
        session = Session.objects.create(
            driver=driver, track=track, mode=Session.Mode.PERFORMANCE, started_at=timezone.now(),
            kart_number=LAPTOP_KART, is_demo=True,
        )
    return {
        "session_id": str(session.id), "driver_id": str(driver.id), "driver_name": driver.name,
        "backend_url": f"{request.scheme}://{request.get_host()}", "device_token": raw_token, "zones": zones,
    }


def link_status(request) -> dict:
    """Where the link is: idle, waiting for the laptop, receiving readings, or quiet (readings stopped)."""
    session = open_link_session()
    if session is None:
        end_link(request)  # a link that ended by itself (the simulator closed it) is cleaned up here
        return {"state": "idle"}
    latest = Telemetry.objects.filter(session=session).order_by("-recorded_at").values_list("recorded_at", flat=True).first()
    age = None if latest is None else max(0.0, (timezone.now() - latest).total_seconds())
    if age is None:
        state = "waiting"
    else:
        state = "receiving" if age <= RECEIVING_WINDOW_SECONDS else "quiet"
    return {
        "state": state, "session_id": str(session.id), "driver_id": str(session.driver_id),
        "driver_name": session.driver.name, "readings": Telemetry.objects.filter(session=session).count(),
        "last_reading_seconds_ago": None if age is None else round(age, 1),
    }
