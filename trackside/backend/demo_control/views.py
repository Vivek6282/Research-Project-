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

from django.http import Http404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotAuthenticated

from accounts.models import AuditLogEntry
from demo_control.simulator import (
    start_simulator,
    stop_simulator,
    get_simulator_status,
    is_demo_tools_enabled,
    is_production_environment,
    AlreadyRunningError,
)


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
    Body: {"mode":"laps","laps":1-20} or {"mode":"continuous"}
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

        try:
            pid = start_simulator(mode=mode, laps=laps)
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
        AuditLogEntry.objects.create(
            actor=request.user,
            action=AuditLogEntry.Action.SIMULATOR_START,
            details=f"Started simulator in mode '{mode}'" + (f" with {laps} laps" if laps else ""),
        )

        return Response(
            {"status": "started", "pid": pid, "mode": mode, "laps": laps},
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
