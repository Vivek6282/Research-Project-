"""
Trackside — Demo Control API Views.

Endpoints:
- POST /api/demo/simulator/start/
- POST /api/demo/simulator/stop/
- GET  /api/demo/simulator/status/

Enforces security rules:
1. 404 when DEMO_TOOLS_ENABLED is not 'true'.
2. 403 when DJANGO_ENV is 'production'.
3. 403 for non-coach roles, 401 for unauthenticated.
4. Fixed command execution, laps must be integer 1..20 (400 on invalid).
5. 409 if already running, stop is idempotent.
6. Writes AuditLogEntry on start and on stop.
"""

import os
import uuid
from dotenv import dotenv_values
from django.conf import settings
from django.db import transaction
from django.core.exceptions import ValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotAuthenticated

from accounts.models import AuditLogEntry
from drivers.models import DriverZoneThreshold
from driving_sessions.models import Session
from tracks.models import Zone
from demo_control.simulator import (
    start_simulator,
    stop_simulator,
    get_simulator_status,
    is_demo_tools_enabled,
    is_production_environment,
    is_simulator_running,
    AlreadyRunningError,
    LIMIT_RANGES,
)


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


class BaseDemoControlView(APIView):
    """
    Base view enforcing demo control feature flag, environment restriction,
    and Coach role-based access control.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        # Rule 1: OFF unless env DEMO_TOOLS_ENABLED=true (default false). When off, every endpoint returns 404.
        if not is_demo_tools_enabled():
            raise Http404("Demo tools are disabled on this server.")

        # Rule 2: Refuse (403) when DJANGO_ENV=production.
        if is_production_environment():
            raise PermissionDenied("Demo tools are disabled in production environment.")

        # Standard authentication
        super().initial(request, *args, **kwargs)

        if not request.user or not request.user.is_authenticated:
            raise NotAuthenticated("Authentication credentials were not provided.")

        # Rule 3: Only role 'coach' may call it (403 for admin, driver and device).
        if getattr(request.user, "role", None) != "coach":
            raise PermissionDenied("Only coaches are permitted to control the demo simulator.")


class SimulatorStartView(BaseDemoControlView):
    """
    POST /api/demo/simulator/start/
    Starts the simulator child process.
    Body: {"mode":"laps","laps":1-20, "limits": {"Hairpin": 1.05, ...}} or {"mode":"continuous", ...}
    """

    def post(self, request, *args, **kwargs):
        data = request.data
        mode = data.get("mode")

        if mode == "continuous":
            laps = None
        elif mode == "laps":
            laps = data.get("laps")
            # laps must be an integer 1..20, otherwise 400
            if type(laps) is not int or laps < 1 or laps > 20:
                return Response(
                    {"error": "laps must be an integer between 1 and 20."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {"error": "mode must be either 'laps' or 'continuous'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate limits if provided
        limits_data = data.get("limits")
        validated_limits = None
        if limits_data is not None:
            if not isinstance(limits_data, dict):
                return Response(
                    {"error": "limits must be an object."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            allowed_corners = set(LIMIT_RANGES.keys())
            for corner in limits_data.keys():
                if corner not in allowed_corners:
                    return Response(
                        {
                            "error": f"Unknown corner '{corner}'. Allowed corners: Hairpin, Sweeper, Chicane."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            validated_limits = {}
            for corner, val in limits_data.items():
                r = LIMIT_RANGES[corner]
                # numbers only (no strings, no booleans)
                if isinstance(val, bool) or not isinstance(val, (int, float)):
                    return Response(
                        {
                            "error": f"Corner limit for '{corner}' must be a number between {r['min']:.2f} and {r['max']:.2f} g."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                val_float = float(val)
                # at most 2 decimals
                if abs(val_float - round(val_float, 2)) > 1e-5:
                    return Response(
                        {
                            "error": f"Corner limit for '{corner}' must have at most 2 decimal places and be between {r['min']:.2f} and {r['max']:.2f} g."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # within range [min, max]
                if val_float < r["min"] or val_float > r["max"]:
                    return Response(
                        {
                            "error": f"Corner limit for '{corner}' must be between {r['min']:.2f} and {r['max']:.2f} g."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                validated_limits[corner] = round(val_float, 2)

        # Rule 5: One simulator run at a time
        if is_simulator_running():
            return Response(
                {"error": "Simulator is already running."},
                status=status.HTTP_409_CONFLICT,
            )

        # Sync limits to backend inside a single transaction before simulator is launched
        if validated_limits is not None:
            limits_synced, limits_note = sync_limits_to_backend(validated_limits, request.user)
        else:
            limits_synced, limits_note = None, None

        try:
            pid = start_simulator(
                mode=mode,
                laps=laps,
                limits=validated_limits,
                limits_synced=limits_synced,
                limits_note=limits_note,
            )
        except AlreadyRunningError:
            return Response(
                {"error": "Simulator is already running."},
                status=status.HTTP_409_CONFLICT,
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to start simulator: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Rule 6: Write an AuditLogEntry on start
        details = f"Started simulator in mode '{mode}'" + (f" with {laps} laps" if laps else "")
        if validated_limits:
            limits_str = ", ".join(f"{k}={v:.2f}" for k, v in validated_limits.items())
            details += f" with custom limits: {limits_str}"

        AuditLogEntry.objects.create(
            actor=request.user,
            action=AuditLogEntry.Action.SIMULATOR_START,
            details=details,
        )

        return Response(
            {
                "status": "started",
                "pid": pid,
                "mode": mode,
                "laps": laps,
                "limits": {
                    corner: (
                        validated_limits[corner]
                        if (validated_limits and corner in validated_limits)
                        else LIMIT_RANGES[corner]["default"]
                    )
                    for corner in ["Hairpin", "Sweeper", "Chicane"]
                },
                "limits_synced": limits_synced,
                "limits_note": limits_note,
            },
            status=status.HTTP_200_OK,
        )


class SimulatorStopView(BaseDemoControlView):
    """
    POST /api/demo/simulator/stop/
    Stops the simulator child process (idempotent).
    """

    def post(self, request, *args, **kwargs):
        was_running = stop_simulator()

        # Rule 6: Write an AuditLogEntry on stop
        AuditLogEntry.objects.create(
            actor=request.user,
            action=AuditLogEntry.Action.SIMULATOR_STOP,
            details="Stopped simulator" if was_running else "Stop requested (simulator was already stopped)",
        )

        return Response({"status": "stopped"}, status=status.HTTP_200_OK)


class SimulatorStatusView(BaseDemoControlView):
    """
    GET /api/demo/simulator/status/
    Returns the current status dictionary of the simulator process.
    """

    def get(self, request, *args, **kwargs):
        status_data = get_simulator_status()
        return Response(status_data, status=status.HTTP_200_OK)
